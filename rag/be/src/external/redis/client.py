"""Redis asyncio client factory.

Only adapter and observability code should import this module directly.
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as redis

from settings import settings

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            health_check_interval=30,
        )
    return _client


async def close_redis_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


RedisValue = str | int | float | bytes
RedisFields = dict[str, RedisValue]
RedisStreamResponse = list[tuple[str, list[tuple[str, dict[str, Any]]]]]
