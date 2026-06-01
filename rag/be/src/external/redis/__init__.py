"""Redis client adapter boundary."""

from external.redis.client import close_redis_client, get_redis_client

__all__ = ["close_redis_client", "get_redis_client"]
