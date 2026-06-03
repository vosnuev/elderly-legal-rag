from __future__ import annotations

import unittest
from unittest.mock import patch

from redis.exceptions import TimeoutError as RedisTimeoutError

from observability.events.models import ObservabilityChannel, ObservabilityEvent
from observability.redis import RedisStreamObservability


class FakeRedis:
    def __init__(self) -> None:
        self.xadd_calls: list[dict] = []
        self.expire_calls: list[tuple[str, int]] = []

    async def xadd(  # noqa: ANN201
        self,
        key,
        fields,
        *,
        maxlen,
        approximate,
    ):
        self.xadd_calls.append(
            {
                "key": key,
                "fields": fields,
                "maxlen": maxlen,
                "approximate": approximate,
            }
        )
        return "1-0"

    async def expire(self, key: str, seconds: int) -> bool:
        self.expire_calls.append((key, seconds))
        return True


class FakeReadRedis:
    def __init__(self) -> None:
        self.xread_calls = 0

    async def xread(self, *, streams, count, block):  # noqa: ANN001, ANN201
        self.xread_calls += 1
        if self.xread_calls == 1:
            raise RedisTimeoutError("idle xread timeout")
        return [
            (
                next(iter(streams)),
                [
                    (
                        "2-0",
                        {
                            "event": _event().model_dump_json(
                                exclude_none=True
                            )
                        },
                    )
                ],
            )
        ]


class RedisStreamObservabilityTest(unittest.IsolatedAsyncioTestCase):
    async def test_publish_refreshes_stream_ttl(self) -> None:
        redis = FakeRedis()
        observer = RedisStreamObservability(
            stream_prefix="rag:observability:jobs",
            maxlen=2000,
            ttl_seconds=3600,
            block_ms=15000,
        )

        with patch("observability.redis.get_redis_client", return_value=redis):
            event_id = await observer.publish(_event())

        self.assertEqual(event_id, "1-0")
        self.assertEqual(
            redis.xadd_calls[0]["key"],
            "rag:observability:jobs:job-1:events",
        )
        self.assertEqual(
            redis.expire_calls,
            [("rag:observability:jobs:job-1:events", 3600)],
        )

    async def test_publish_can_disable_stream_ttl(self) -> None:
        redis = FakeRedis()
        observer = RedisStreamObservability(
            stream_prefix="rag:observability:jobs",
            maxlen=2000,
            ttl_seconds=0,
            block_ms=15000,
        )

        with patch("observability.redis.get_redis_client", return_value=redis):
            await observer.publish(_event())

        self.assertEqual(redis.expire_calls, [])

    async def test_read_keeps_stream_alive_on_idle_timeout(self) -> None:
        redis = FakeReadRedis()
        observer = RedisStreamObservability(
            stream_prefix="rag:observability:jobs",
            maxlen=2000,
            ttl_seconds=3600,
            block_ms=15000,
        )

        with patch("observability.redis.get_redis_client", return_value=redis):
            event = await anext(
                observer.read(job_id="job-1", last_event_id="0-0")
            )

        self.assertEqual(redis.xread_calls, 2)
        self.assertEqual(event.event_id, "2-0")
        self.assertEqual(event.job_id, "job-1")


def _event() -> ObservabilityEvent:
    return ObservabilityEvent(
        job_id="job-1",
        channel=ObservabilityChannel.AGENT_TRANSCRIPT,
        payload={"type": "agent", "log": "hello"},
    )


if __name__ == "__main__":
    unittest.main()
