import os
from functools import lru_cache

import redis
from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6380")),
        decode_responses=True,
    )