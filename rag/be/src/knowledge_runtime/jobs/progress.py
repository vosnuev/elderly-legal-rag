# 역할: worker가 받은 graph 실행 결과를 job-level progress로 확정하고 IngestJob에 저장하는 modifier이다.
from __future__ import annotations

from dataclasses import dataclass

from knowledge_runtime.jobs.models import JobPhase, JobRecord
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.tasks.models import TaskKind, TaskRecord
from observability.logger import bind_logger
from pipeline.schemas import GraphIngestPhase, IngestGraphResult
from query.read.runtime import summarize_candidate_review_progress
from query.write import upsert_ingest_job_progress


@dataclass(frozen=True)
class CandidateProgress:
    candidate_count: int
    pending_review_count: int


class JobProgressModifier:
    def __init__(self, *, job_store: JobStore) -> None:
        self._job_store = job_store
        self._logger = bind_logger(component="job_progress_modifier")

    def apply_task_result(
        self,
        *,
        task: TaskRecord,
        result: IngestGraphResult,
    ) -> JobRecord | None:
        final_result = self._final_result_for_task(task=task, result=result)
        self._persist(final_result)
        updated = self._job_store.apply_pipeline_result(final_result)
        self._logger.bind(
            job_id=task.job_id,
            task_id=task.task_id,
            kind=task.kind.value,
            incoming_phase=result.phase.value,
            final_phase=final_result.phase.value,
            document_id=final_result.document_id,
            chunk_count=final_result.chunk_count,
            candidate_count=final_result.candidate_count,
            pending_review_count=final_result.pending_review_count,
        ).info("job progress applied")
        return updated

    def mark_task_failed(self, *, task: TaskRecord, error: str) -> JobRecord:
        failed = self._job_store.mark_failed(
            job_id=task.job_id,
            file_name="unknown",
            message=error,
        )
        self._persist(
            IngestGraphResult(
                job_id=failed.job_id,
                phase=GraphIngestPhase.FAILED,
                document_id=failed.document_id,
                chunk_count=failed.chunk_count,
                candidate_count=failed.candidate_count,
                pending_review_count=failed.pending_review_count,
                errors=[error],
            )
        )
        self._logger.bind(
            job_id=task.job_id,
            task_id=task.task_id,
            kind=task.kind.value,
            error=error,
        ).warning("job progress marked failed")
        return failed

    def _final_result_for_task(
        self,
        *,
        task: TaskRecord,
        result: IngestGraphResult,
    ) -> IngestGraphResult:
        base = _result_with_job_id(result=result, job_id=task.job_id)
        if base.phase is GraphIngestPhase.FAILED:
            return self._merge_existing_progress(base)
        if task.kind is TaskKind.BUILD:
            return self._build_result(base)
        if task.kind is TaskKind.REVIEW:
            return self._review_result(task=task, result=base)
        raise ValueError(f"Unsupported task kind: {task.kind}")

    def _build_result(self, result: IngestGraphResult) -> IngestGraphResult:
        progress = _candidate_progress(job_id=result.job_id)
        candidate_count = _first_known(progress.candidate_count, result.candidate_count)
        pending_review_count = _first_known(
            progress.pending_review_count,
            result.pending_review_count,
        )
        return result.model_copy(
            update={
                "phase": _phase_for_pending_count(pending_review_count),
                "candidate_count": candidate_count,
                "pending_review_count": pending_review_count,
            }
        )

    def _review_result(
        self,
        *,
        task: TaskRecord,
        result: IngestGraphResult,
    ) -> IngestGraphResult:
        existing = self._job_store.get(task.job_id)
        progress = _candidate_progress(job_id=task.job_id)
        candidate_count = _first_known(
            progress.candidate_count,
            existing.candidate_count if existing else result.candidate_count,
        )
        pending_review_count = _first_known(
            progress.pending_review_count,
            result.pending_review_count,
        )
        return result.model_copy(
            update={
                "phase": _phase_for_pending_count(pending_review_count),
                "document_id": existing.document_id if existing else result.document_id,
                "chunk_count": existing.chunk_count if existing else result.chunk_count,
                "candidate_count": candidate_count,
                "pending_review_count": pending_review_count,
            }
        )

    def _merge_existing_progress(self, result: IngestGraphResult) -> IngestGraphResult:
        existing = self._job_store.get(result.job_id)
        if existing is None:
            return result
        return result.model_copy(
            update={
                "document_id": result.document_id or existing.document_id,
                "chunk_count": result.chunk_count or existing.chunk_count,
                "candidate_count": result.candidate_count or existing.candidate_count,
                "pending_review_count": (
                    result.pending_review_count or existing.pending_review_count
                ),
            }
        )

    def _persist(self, result: IngestGraphResult) -> None:
        upsert_ingest_job_progress(
            job_id=result.job_id,
            phase=result.phase.value,
            document_id=result.document_id,
            chunk_count=result.chunk_count,
            candidate_count=result.candidate_count,
            pending_review_count=result.pending_review_count,
            warnings=result.warnings,
            errors=result.errors,
        )
        self._logger.bind(
            job_id=result.job_id,
            phase=result.phase.value,
            document_id=result.document_id,
            chunk_count=result.chunk_count,
            candidate_count=result.candidate_count,
            pending_review_count=result.pending_review_count,
            error_count=len(result.errors),
            warning_count=len(result.warnings),
        ).info("ingest job progress persisted")


def _result_with_job_id(*, result: IngestGraphResult, job_id: str) -> IngestGraphResult:
    if result.job_id:
        return result
    return result.model_copy(update={"job_id": job_id})


def _candidate_progress(*, job_id: str) -> CandidateProgress:
    result = summarize_candidate_review_progress(job_id)
    rows = result.get("rows") or []
    if not rows:
        return CandidateProgress(candidate_count=0, pending_review_count=0)
    row = rows[0]
    return CandidateProgress(
        candidate_count=int(row.get("candidate_count") or 0),
        pending_review_count=int(row.get("pending_review_count") or 0),
    )


def _phase_for_pending_count(pending_review_count: int) -> GraphIngestPhase:
    if pending_review_count > 0:
        return GraphIngestPhase.PENDING_REVIEW
    return GraphIngestPhase.COMPLETED


def _first_known(primary: int, fallback: int) -> int:
    if primary > 0:
        return primary
    return fallback
