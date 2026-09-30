from fastapi import FastAPI
from pydantic import BaseModel

from agent import collect_system_metrics

class MemoryMetrics(BaseModel):
    total: int
    available: int
    used: int
    used_percent: float

class DiskMetrics(BaseModel):
    total: int
    used: int
    free: int
    used_percent: float

class NetworkMetrics(BaseModel):
    rx_speed: int
    tx_speed: int

class SystemMetrics(BaseModel):
    memory: MemoryMetrics
    cpu_usage: float
    hostname: str
    uptime: str
    disk: DiskMetrics
    network: NetworkMetrics

app = FastAPI()

@app.get("/")
def root():
    return {"Message" : "InfraWatch Agent is running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "InfraWatch Agent",
    }

@app.get("/metrics")
def metrics():
    return collect_system_metrics()