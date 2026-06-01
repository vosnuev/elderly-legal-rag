"""Redis Streams implementation for job observability events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

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
        block_ms: int,
        count: int = 50,
    ) -> None:
        self._stream_prefix = stream_prefix.rstrip(":")
        self._maxlen = maxlen
        self._block_ms = block_ms
        self._count = count

    @classmethod
    def from_settings(cls) -> "RedisStreamObservability":
        return cls(
            stream_prefix=settings.observability_stream_prefix,
            maxlen=settings.observability_stream_maxlen,
            block_ms=settings.observability_xread_block_ms,
        )

    async def publish(self, event: ObservabilityEvent) -> str:
        redis = get_redis_client()
        event_id = await redis.xadd(
            self._key(event.job_id),
            {_EVENT_FIELD: event.model_dump_json(exclude_none=True)},
            maxlen=self._maxlen,
            approximate=True,
        )
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
            response = await redis.xread(
                streams={key: current_id},
                count=self._count,
                block=self._block_ms,
            )
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
