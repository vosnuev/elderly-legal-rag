from __future__ import annotations

from pipeline.schemas import GraphIngestPhase, IngestGraphResult
from ingest_tasks.schemas import (
    FileIngestStatusResponse,
    IngestStage,
    IngestStageResult,
    StageStatus,
)


class IngestJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, FileIngestStatusResponse] = {}

    def save(self, response: FileIngestStatusResponse) -> FileIngestStatusResponse:
        self._jobs[response.job_id] = response
        return response

    def get(self, job_id: str) -> FileIngestStatusResponse | None:
        return self._jobs.get(job_id)


def create_missing_job_response(job_id: str) -> FileIngestStatusResponse:
    return FileIngestStatusResponse(
        job_id=job_id,
        file_name="unknown",
        current_stage=IngestStage.FAILED,
        completed=False,
        stages=[
            IngestStageResult(
                stage=IngestStage.FAILED,
                status=StageStatus.FAILED,
                message="No ingest status was found for this job_id.",
            )
        ],
        warning="No ingest status was found for this job_id.",
    )


def failed_ingest_response(
    *,
    job_id: str,
    file_name: str,
    stages: list[IngestStageResult],
    message: str,
) -> FileIngestStatusResponse:
    stages.append(
        IngestStageResult(
            stage=IngestStage.FAILED,
            status=StageStatus.FAILED,
            message=message,
        )
    )
    return FileIngestStatusResponse(
        job_id=job_id,
        file_name=file_name,
        current_stage=IngestStage.FAILED,
        completed=False,
        stages=stages,
        warning=message,
    )


def apply_graph_ingest_result(
    job: FileIngestStatusResponse,
    result: IngestGraphResult,
    store: IngestJobStore,
) -> FileIngestStatusResponse:
    stages = list(job.stages)
    stage = _stage_from_graph_phase(result.phase)
    status = StageStatus.FAILED if result.phase is GraphIngestPhase.FAILED else StageStatus.SUCCESS
    stages.append(
        IngestStageResult(
            stage=stage,
            status=status,
            message=_graph_result_message(result),
            error="; ".join(result.errors) if result.errors else None,
        )
    )
    completed = result.phase in {
        GraphIngestPhase.PENDING_REVIEW,
        GraphIngestPhase.COMPLETED,
        GraphIngestPhase.FAILED,
        GraphIngestPhase.NEEDS_RETRY,
    }
    return store.save(
        FileIngestStatusResponse(
            job_id=job.job_id,
            file_name=job.file_name,
            current_stage=stage,
            completed=completed,
            stages=stages,
            warning="; ".join(result.warnings) if result.warnings else None,
            document_id=result.document_id or job.document_id,
            chunk_count=result.chunk_count,
            candidate_count=result.candidate_count,
            pending_review_count=result.pending_review_count,
        )
    )


def _stage_from_graph_phase(phase: GraphIngestPhase) -> IngestStage:
    mapping = {
        GraphIngestPhase.GRAPH_ADD_STARTED: IngestStage.GRAPH_ADD_STARTED,
        GraphIngestPhase.DOCUMENT_REGISTERED: IngestStage.DOCUMENT_REGISTERED,
        GraphIngestPhase.CHUNKED: IngestStage.CHUNKED,
        GraphIngestPhase.CHUNKS_STORED: IngestStage.CHUNKS_STORED,
        GraphIngestPhase.EMBEDDING_DISPATCHED: IngestStage.EMBEDDING_DISPATCHED,
        GraphIngestPhase.CANDIDATES_GENERATED: IngestStage.CANDIDATES_GENERATED,
        GraphIngestPhase.PENDING_REVIEW: IngestStage.PENDING_REVIEW,
        GraphIngestPhase.NEEDS_RETRY: IngestStage.NEEDS_RETRY,
        GraphIngestPhase.COMPLETED: IngestStage.COMPLETED,
        GraphIngestPhase.FAILED: IngestStage.FAILED,
    }
    return mapping.get(phase, IngestStage.GRAPH_ADD_STARTED)


def _graph_result_message(result: IngestGraphResult) -> str:
    if result.phase is GraphIngestPhase.PENDING_REVIEW:
        return "Graph ingest is pending relationship candidate review."
    if result.phase is GraphIngestPhase.COMPLETED:
        return "Graph ingest completed without pending relationship candidates."
    if result.phase is GraphIngestPhase.NEEDS_RETRY:
        return "Graph ingest needs retry before review."
    if result.phase is GraphIngestPhase.FAILED:
        return "Graph ingest failed."
    return f"Graph ingest reached phase: {result.phase.value}."
