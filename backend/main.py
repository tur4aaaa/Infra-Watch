from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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


app = FastAPI(title="InfraWatch")


@app.get("/")
def root():
    return {"message": "InfraWatch is running"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "InfraWatch"}


@app.get("/metrics", response_model=SystemMetrics)
def metrics():
    return collect_system_metrics()


@app.get("/redis-test")
def redis_test():
    try:
        client = get_redis_client()
        client.set("infra_watch_test", "ok")
        return {"redis": client.get("infra_watch_test")}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Redis is unavailable: {error}")