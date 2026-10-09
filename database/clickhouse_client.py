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