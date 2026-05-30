from __future__ import annotations

from agents.graph_ingest.orchestrator import GraphIngestOrchestrator
from agents.graph_ingest.schemas import IngestGraphResult
from ingest_tasks.schemas import FileIngestStatusResponse
from logger import bind_logger
from query.service import MemgraphQueryService


class IngestTaskQueue:
    """In-process task queue boundary for graph ingest jobs.

    This keeps API/job orchestration separate from the LangGraph runtime. It is
    synchronous for MVP, but the caller only passes job/document identifiers.
    """

    def __init__(
        self,
        graph_orchestrator: GraphIngestOrchestrator | None = None,
        query_service: MemgraphQueryService | None = None,
    ) -> None:
        self._graph_orchestrator = graph_orchestrator or GraphIngestOrchestrator(query_service)
        self._logger = bind_logger(component="ingest_task_queue")

    def start(self, job: FileIngestStatusResponse) -> IngestGraphResult:
        if not job.document_id:
            raise ValueError("Cannot start graph ingest without document_id.")

        self._logger.bind(
            job_id=job.job_id,
            document_id=job.document_id,
        ).info("ingest task started")
        result = self._graph_orchestrator.start_construction(
            job_id=job.job_id,
            document_id=job.document_id,
        )
        self._logger.bind(
            job_id=job.job_id,
            document_id=job.document_id,
            phase=result.phase.value,
        ).info("ingest task finished")
        return result
