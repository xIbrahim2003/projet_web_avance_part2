import os
import redis

redis_url = os.getenv("REDIS_URL", "redis://localhost")
redis_client = redis.Redis.from_url(redis_url)