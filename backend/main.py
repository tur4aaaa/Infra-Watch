from contextlib import asynccontextmanager
from datetime import datetime, timezone

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from clickhouse_connect.driver.exceptions import OperationalError


from fastapi import FastAPI, HTTPException,Query
from clickhouse_connect.driver.exceptions import OperationalError
from pydantic import BaseModel

from database.clickhouse_client import get_clickhouse_client, init_db
from agent import collect_system_metrics
from database.redis_client import get_redis_client


class MemoryMetrics(BaseModel):
    total_kb: int
    available_kb: int
    used_kb: int
    used_percent: float


class DiskMetrics(BaseModel):
    total_bytes: int
    used_bytes: int
    free_bytes: int
    used_percent: float


class NetworkMetrics(BaseModel):
    rx_bytes_per_sec: int
    tx_bytes_per_sec: int


class SystemMetrics(BaseModel):
    hostname: str
    timestamp: int
    uptime_seconds: int
    cpu_usage: float
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics

COLUMNS = [
    "hostname",
    "timestamp",
    "uptime_seconds",
    "cpu_usage",
    "memory_total_kb",
    "memory_available_kb",
    "memory_used_kb",
    "memory_used_percent",
    "disk_total_bytes",
    "disk_used_bytes",
    "disk_free_bytes",
    "disk_used_percent",
    "network_rx_bytes_per_sec",
    "network_tx_bytes_per_sec",
]

def metrics_to_row(m: SystemMetrics) -> list:
    return [
        m.hostname,
        datetime.fromtimestamp(m.timestamp, tz=timezone.utc),
        m.uptime_seconds,
        m.cpu_usage,
        m.memory.total_kb,
        m.memory.available_kb,
        m.memory.used_kb,
        m.memory.used_percent,
        m.disk.total_bytes,
        m.disk.used_bytes,
        m.disk.free_bytes,
        m.disk.used_percent,
        m.network.rx_bytes_per_sec,
        m.network.tx_bytes_per_sec,
    ]

@asynccontextmanager
async def lifaspan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="InfraWatch",lifespan=lifaspan)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/server/{hostname}", include_in_schema=False)
def server_page(hostname:str):
    return FileResponse(FRONTEND_DIR / "server.html")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "InfraWatch"}


@app.get("/metrics", response_model=SystemMetrics)
def metrics():
    return collect_system_metrics()

@app.post("/metrics", status_code=201) #default status code for successful creation
def receive_metrics(metrics: SystemMetrics):
    try:
        client = get_clickhouse_client()
        client.insert("system_metrics",[metrics_to_row(metrics)],column_names=COLUMNS)
    except Exception as error: # If ClickHouse is unavailable, return a 503 Service Unavailable response
        raise HTTPException(status_code=503, detail=f"ClickHouse is unavailable: {error}")
    return {"message": "Metrics received and stored successfully"}

@app.get("/redis-test")
def redis_test():
    try:
        client = get_redis_client()
        client.set("infra_watch_test", "ok")
        return {"redis": client.get("infra_watch_test")}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Redis is unavailable: {error}")


ONLINE_THRESHIOLD_SECONDS = 60 #If more that 60secs, the agent is considered offline
@app.get("/servers")
def list_servers():
    try:
        result = get_clickhouse_client().query("""
        SELECT
            hostname,
            toUnixTimestamp(max(timestamp)) AS last_seen,
            dateDiff('second', max(timestamp),now()) AS seconds_ago,
            argMax(cpu_usage,timestamp)AS cpu_usage,
            argMax(memory_used_percent,timestamp) AS memory_used_percent,
            argMax(disk_used_percent,timestamp) AS disk_used_percent
        FROM system_metrics
        GROUP BY hostname
        ORDER BY hostname
        """)
    except OperationalError as error:
        raise HTTPException(status_code=503,detail=f"ClickHouse is unavailable: {error}")

    servers = []
    for row in result.named_results():
        row["online"] = row["seconds_ago"] <= ONLINE_THRESHIOLD_SECONDS
        servers.append(row)
    return servers

@app.get("/metrics/history")
def metrics_history(
    hostname: str,
    minutes:int = Query(60, ge=1, le=7 * 24 * 60), #g = greater or equal, l = less or equal
):
    step = max(10,minutes * 60 // 300)

    try:
        result = get_clickhouse_client().query(
            """
            SELECT
                toUnixTimestamp(toStartOfInterval(timestamp, toIntervalSecond({step:UInt32}))) AS ts,
                round(avg(cpu_usage), 2)                AS cpu_usage,
                round(avg(memory_used_percent), 2)      AS memory_used_percent,
                round(avg(disk_used_percent), 2)        AS disk_used_percent,
                round(avg(network_rx_bytes_per_sec))    AS rx_bytes_per_sec,
                round(avg(network_tx_bytes_per_sec))    AS tx_bytes_per_sec
            FROM system_metrics
            WHERE hostname = {hostname:String} 
              AND timestamp >= now() - toIntervalMinute({minutes:UInt32})
            GROUP BY ts
            ORDER BY ts
            """,
            parameters={"hostname": hostname, "step": step, "minutes": minutes},
        )
    except OperationalError as error:
        raise HTTPException(status_code=503, detail=f"ClickHouse is unavailable: {error}")

    return {
        "hostname": hostname,
        "minutes":minutes,
        "step_seconds":step,
        "points": list(result.named_results()),
    }