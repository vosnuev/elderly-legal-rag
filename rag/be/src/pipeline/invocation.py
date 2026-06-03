from __future__ import annotations

from logger import bind_logger
from pipeline.graphs.candidate_review_graph import CandidateReviewGraph
from pipeline.graphs.document_construction_graph import DocumentConstructionGraph
from pipeline.schemas import GraphIngestPhase, IngestGraphResult, ReviewAction
from pipeline.services.ingest_progress_service import IngestProgressService


class GraphIngestInvocation:
    """Facade for the two graph ingest flows used by the task queue."""

    def __init__(self) -> None:
        self._document_construction_graph = DocumentConstructionGraph()
        self._candidate_review_graph = CandidateReviewGraph()
        self._ingest_progress_service = IngestProgressService()
        self._logger = bind_logger(component="graph_ingest_invocation")

    def start_construction(
        self,
        *,
        job_id: str,
        document_id: str,
    ) -> IngestGraphResult:
        try:
            self._logger.bind(
                job_id=job_id,
                document_id=document_id,
            ).info("graph construction invoked")
            return self._document_construction_graph.invoke(
                job_id=job_id,
                document_id=document_id,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.bind(
                job_id=job_id,
                document_id=document_id,
            ).exception("graph construction failed")
            return self._ingest_progress_service.mark(
                job_id=job_id,
                phase=GraphIngestPhase.FAILED,
                document_id=document_id,
                chunk_count=0,
                candidate_count=0,
                errors=[str(exc)],
            )

    def apply_review_decision(
        self,
        *,
        candidate_id: str,
        action: ReviewAction,
        reviewer: str,
        note: str | None = None,
    ) -> IngestGraphResult:
        try:
            self._logger.bind(
                candidate_id=candidate_id,
                action=action.value,
                reviewer=reviewer,
            ).info("candidate review action invoked")
            return self._candidate_review_graph.invoke(
                candidate_id=candidate_id,
                action=action,
                reviewer=reviewer,
                note=note,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.bind(
                candidate_id=candidate_id,
                action=action.value,
                reviewer=reviewer,
            ).exception("candidate review action failed")
            return IngestGraphResult(
                job_id="",
                phase=GraphIngestPhase.FAILED,
                errors=[str(exc)],
            )
