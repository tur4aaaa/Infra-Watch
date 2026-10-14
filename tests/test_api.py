from datetime import datetime, timezone

import pytest
from clickhouse_connect.driver.exceptions import OperationalError
from fastapi.testclient import TestClient

from backend import main


# Fake backend for testing

class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def named_results(self):
        return iter(self.rows)


class FakeClickHouse:
    
    def __init__(self):
        self.rows = []      
        self.fail = False   
        self.inserts = []   
        self.queries = []   

    def insert(self, table, data, column_names):
        if self.fail:
            raise OperationalError("connection refused")
        self.inserts.append({"table": table, "data": data, "columns": column_names})

    def query(self, sql, parameters=None):
        if self.fail:
            raise OperationalError("connection refused")
        self.queries.append({"sql": sql, "parameters": parameters})
        return FakeResult(self.rows)



@pytest.fixture
def fake_db(monkeypatch):
    db = FakeClickHouse()
    monkeypatch.setattr(main, "get_clickhouse_client", lambda: db)  # подсовываем фальшивку backend'у
    return db


@pytest.fixture
def client():
    return TestClient(main.app)   


VALID_METRICS = {
    "hostname": "web-1",
    "timestamp": 1791540000,
    "uptime_seconds": 3600,
    "cpu_usage": 12.5,
    "memory": {"total_kb": 16000000, "available_kb": 12000000, "used_kb": 4000000, "used_percent": 25.0},
    "disk": {"total_bytes": 500, "used_bytes": 150, "free_bytes": 350, "used_percent": 30.0},
    "network": {"rx_bytes_per_sec": 1024, "tx_bytes_per_sec": 512},
}




def test_post_metrics_stores_flat_row(client, fake_db):
    response = client.post("/metrics", json=VALID_METRICS)

    assert response.status_code == 201
    assert len(fake_db.inserts) == 1

    insert = fake_db.inserts[0]
    row = dict(zip(insert["columns"], insert["data"][0]))  

    assert insert["table"] == "system_metrics"
    assert row["hostname"] == "web-1"
    assert row["memory_used_percent"] == 25.0
    assert row["network_tx_bytes_per_sec"] == 512
    assert row["timestamp"] == datetime.fromtimestamp(1791540000, tz=timezone.utc)


def test_post_metrics_rejects_missing_field(client, fake_db):
    broken = {k: v for k, v in VALID_METRICS.items() if k != "cpu_usage"}

    response = client.post("/metrics", json=broken)

    assert response.status_code == 422
    assert fake_db.inserts == []   


def test_post_metrics_returns_503_when_db_is_down(client, fake_db):
    fake_db.fail = True

    response = client.post("/metrics", json=VALID_METRICS)

    assert response.status_code == 503




def test_servers_marks_online_and_offline(client, fake_db):
    fake_db.rows = [
        {"hostname": "alive", "seconds_ago": 5},
        {"hostname": "dead", "seconds_ago": 600},
    ]

    servers = client.get("/servers").json()

    status = {s["hostname"]: s["online"] for s in servers}
    assert status == {"alive": True, "dead": False}




def test_history_rejects_bad_minutes(client, fake_db):
    assert client.get("/metrics/history", params={"hostname": "x", "minutes": 0}).status_code == 422
    assert client.get("/metrics/history", params={"hostname": "x", "minutes": 999999}).status_code == 422


def test_history_requires_hostname(client, fake_db):
    assert client.get("/metrics/history").status_code == 422


def test_history_passes_hostname_as_parameter_not_sql(client, fake_db):
    evil = "x' OR 1=1 --"

    client.get("/metrics/history", params={"hostname": evil, "minutes": 60})

    query = fake_db.queries[0]
    assert query["parameters"]["hostname"] == evil   
    assert evil not in query["sql"]                   