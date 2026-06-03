"""Job status and event stream service."""

from __future__ import annotations

from fastapi.responses import StreamingResponse

from knowledge_runtime.jobs.projector import JobProjector
from knowledge_runtime.schemas import JobStatusResponse
from observability.events.ports import ObservabilityReader
from observability.expose.sse import observability_stream_response


class StatusService:
    def __init__(
        self,
        *,
        projector: JobProjector,
        observer: ObservabilityReader,
    ) -> None:
        self._projector = projector
        self._observer = observer

    def get(self, job_id: str) -> JobStatusResponse:
        return self._projector.status(job_id)

    def list(self, *, limit: int = 50) -> list[JobStatusResponse]:
        return self._projector.list(limit=limit)

    def events(self, job_id: str, *, last_event_id: str = "0-0") -> StreamingResponse:
        return observability_stream_response(
            self._observer,
            job_id=job_id,
            last_event_id=last_event_id,
        )
