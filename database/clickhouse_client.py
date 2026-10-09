import os
from functools import lru_cache

import clickhouse_connect
from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8124")),
        username=os.getenv("CLICKHOUSE_USER", "infra"),
        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
    )

def init_db():
    client = get_clickhouse_client()
    client.command(
        """
        CREATE TABLE IF NOT EXISTS system_metrics (
            hostname String,
            timestamp DateTime,
            uptime_seconds UInt64,
            cpu_usage Float32,
            memory_total_kb UInt64,
            memory_available_kb UInt64,
            memory_used_kb UInt64,
            memory_used_percent Float32,
            disk_total_bytes UInt64,
            disk_used_bytes UInt64,
            disk_free_bytes UInt64,
            disk_used_percent Float32,
            network_rx_bytes_per_sec UInt64,
            network_tx_bytes_per_sec UInt64
        ) ENGINE = MergeTree()
        ORDER BY (hostname, timestamp)
        """
    )


if __name__ == "__main__":
    init_db()
    print(get_clickhouse_client().command("SHOW TABLES"))