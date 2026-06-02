"""Build FE-facing job snapshots from stored job progress and task state."""

from __future__ import annotations

from knowledge_runtime.jobs.models import JobPhase, JobRecord, JobStage, JobStageStatus
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.schemas import JobStatusResponse, TaskSnapshot
from knowledge_runtime.tasks.models import TaskRecord
from knowledge_runtime.tasks.store import TaskStore
from query.read.runtime import summarize_job_progress


class JobProjector:
    def __init__(self, *, job_store: JobStore, task_store: TaskStore) -> None:
        self._job_store = job_store
        self._task_store = task_store

    def status(self, job_id: str) -> JobStatusResponse:
        record = self._job_store.get(job_id)
        if record is None:
            return _missing_job(job_id)

        merged = self._merge_persisted_progress(record)
        return _response_from_record(
            merged,
            current_task=self._task_store.current_for_job(job_id),
        )

    def _merge_persisted_progress(self, record: JobRecord) -> JobRecord:
        try:
            result = summarize_job_progress(record.job_id)
        except Exception:  # noqa: BLE001
            return record
        rows = result.get("rows") or []
        if not rows:
            return record

        row = rows[0]
        job_props = _properties(row.get("job") or {})
        merged = record.model_copy(deep=True)
        if job_props.get("phase"):
            merged.current_phase = JobPhase.normalize(job_props["phase"])
        merged.document_id = str(
            job_props.get("document_id") or merged.document_id or ""
        ) or None
        merged.chunk_count = int(job_props.get("chunk_count") or row.get("chunk_count") or 0)
        merged.candidate_count = int(
            job_props.get("candidate_count") or row.get("candidate_count") or 0
        )
        merged.pending_review_count = int(
            job_props.get("pending_review_count")
            or row.get("pending_review_count")
            or 0
        )
        return merged


def _response_from_record(
    record: JobRecord,
    *,
    current_task: TaskRecord | None,
) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=record.job_id,
        file_name=record.file_name,
        current_phase=record.current_phase,
        completed=record.completed,
        stages=record.stages,
        warning=record.warning,
        document_id=record.document_id,
        chunk_count=record.chunk_count,
        candidate_count=record.candidate_count,
        pending_review_count=record.pending_review_count,
        current_task=_task_snapshot(current_task) if current_task else None,
    )


def _task_snapshot(task: TaskRecord) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=task.task_id,
        kind=task.kind.value,
        status=task.status.value,
        idempotency_key=task.idempotency_key,
        submitted_at=task.submitted_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
        error=task.error,
    )


def _missing_job(job_id: str) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job_id,
        file_name="unknown",
        current_phase=JobPhase.FAILED,
        completed=True,
        stages=[
            JobStage(
                phase=JobPhase.FAILED,
                status=JobStageStatus.FAILED,
                message="Job not found.",
                error="Job not found.",
            )
        ],
    )


def _properties(record: object) -> dict[str, object]:
    if not isinstance(record, dict):
        return {}
    nested = record.get("properties")
    if isinstance(nested, dict):
        return nested
    return record
