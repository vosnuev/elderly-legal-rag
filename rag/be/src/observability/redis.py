"""Redis Streams implementation for job observability events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from redis.exceptions import TimeoutError as RedisTimeoutError

from external.redis import get_redis_client
from observability.events.models import ObservabilityEvent
from settings import settings

_EVENT_FIELD = "event"


class RedisStreamObservability:
    def __init__(
        self,
        *,
        stream_prefix: str,
        maxlen: int,
        ttl_seconds: int,
        block_ms: int,
        count: int = 50,
    ) -> None:
        self._stream_prefix = stream_prefix.rstrip(":")
        self._maxlen = maxlen
        self._ttl_seconds = ttl_seconds
        self._block_ms = block_ms
        self._count = count

    @classmethod
    def from_settings(cls) -> "RedisStreamObservability":
        return cls(
            stream_prefix=settings.observability_stream_prefix,
            maxlen=settings.observability_stream_maxlen,
            ttl_seconds=settings.observability_stream_ttl_seconds,
            block_ms=settings.observability_xread_block_ms,
        )

    async def publish(self, event: ObservabilityEvent) -> str:
        redis = get_redis_client()
        key = self._key(event.job_id)
        event_id = await redis.xadd(
            key,
            {_EVENT_FIELD: event.model_dump_json(exclude_none=True)},
            maxlen=self._maxlen,
            approximate=True,
        )
        if self._ttl_seconds > 0:
            # Redis Streams are per-job debugging artifacts. Refreshing TTL on
            # every publish keeps active jobs visible while automatically
            # removing old transcript noise after the configured window.
            await redis.expire(key, self._ttl_seconds)
        return str(event_id)

    async def read(
        self,
        *,
        job_id: str,
        last_event_id: str,
    ) -> AsyncIterator[ObservabilityEvent]:
        redis = get_redis_client()
        current_id = last_event_id
        key = self._key(job_id)
        while True:
            try:
                response = await redis.xread(
                    streams={key: current_id},
                    count=self._count,
                    block=self._block_ms,
                )
            except RedisTimeoutError:
                # A blocking XREAD can hit the client socket timeout before a new
                # event arrives. That is an idle poll, not a broken SSE stream.
                await asyncio.sleep(0)
                continue
            if not response:
                await asyncio.sleep(0)
                continue

            for _stream, entries in response:
                for event_id, fields in entries:
                    current_id = str(event_id)
                    event = _event_from_fields(fields)
                    if event is not None:
                        yield event.with_event_id(current_id)

    def _key(self, job_id: str) -> str:
        return f"{self._stream_prefix}:{job_id}:events"


def _event_from_fields(fields: dict[str, Any]) -> ObservabilityEvent | None:
    raw = fields.get(_EVENT_FIELD)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        payload = json.loads(raw)
    elif isinstance(raw, dict):
        payload = raw
    else:
        return None
    return ObservabilityEvent.model_validate(payload)
