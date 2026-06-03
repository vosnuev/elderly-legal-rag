"""FastAPI SSE adapter for exposing job observability streams."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

from observability.events.models import ObservabilityEvent
from observability.events.ports import ObservabilityReader


def observability_stream_response(
    reader: ObservabilityReader,
    *,
    job_id: str,
    last_event_id: str = "0-0",
) -> StreamingResponse:
    return StreamingResponse(
        _serialize(reader.read(job_id=job_id, last_event_id=last_event_id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _serialize(events: AsyncIterator[ObservabilityEvent]) -> AsyncIterator[str]:
    async for event in events:
        event_name = str(event.channel)
        event_id = event.event_id or ""
        yield f"id: {event_id}\nevent: {event_name}\ndata: {event.model_dump_json()}\n\n"
