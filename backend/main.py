from contextlib import asynccontextmanager
from datetime import datetime, timezone


from fastapi import FastAPI, HTTPException
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


@app.get("/")
def root():
    return {"message": "InfraWatch is running"}


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