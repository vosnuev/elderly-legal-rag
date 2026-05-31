from __future__ import annotations

from pipeline.invocation import GraphIngestInvocation
from pipeline.schemas import IngestGraphResult, ReviewAction
from ingest_tasks.schemas import FileIngestStatusResponse
from logger import bind_logger


class IngestTaskQueue:
    """In-process task queue boundary for graph ingest jobs.

    This keeps API/job orchestration separate from the LangGraph runtime. It is
    synchronous for MVP, but the caller only passes job/document identifiers.
    """

    def __init__(
        self,
        graph_invocation: GraphIngestInvocation | None = None,
    ) -> None:
        self._graph_invocation = graph_invocation or GraphIngestInvocation()
        self._logger = bind_logger(component="ingest_task_queue")

    def start(self, job: FileIngestStatusResponse) -> IngestGraphResult:
        if not job.document_id:
            raise ValueError("Cannot start graph ingest without document_id.")

        self._logger.bind(
            job_id=job.job_id,
            document_id=job.document_id,
        ).info("ingest task started")
        result = self._graph_invocation.start_construction(
            job_id=job.job_id,
            document_id=job.document_id,
        )
        self._logger.bind(
            job_id=job.job_id,
            document_id=job.document_id,
            phase=result.phase.value,
        ).info("ingest task finished")
        return result

    def apply_review_decision(
        self,
        *,
        candidate_id: str,
        action: ReviewAction,
        reviewer: str,
        note: str | None = None,
    ) -> IngestGraphResult:
        self._logger.bind(
            candidate_id=candidate_id,
            action=action.value,
            reviewer=reviewer,
        ).info("review task started")
        result = self._graph_invocation.apply_review_decision(
            candidate_id=candidate_id,
            action=action,
            reviewer=reviewer,
            note=note,
        )
        self._logger.bind(
            candidate_id=candidate_id,
            action=action.value,
            phase=result.phase.value,
        ).info("review task finished")
        return result
