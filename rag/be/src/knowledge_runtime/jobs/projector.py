"""Build FE-facing job snapshots from persisted progress and runtime state."""

from __future__ import annotations

from datetime import UTC, datetime

from knowledge_runtime.jobs.models import JobPhase, JobRecord, JobStage, JobStageStatus
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.schemas import JobStatusResponse, TaskSnapshot
from knowledge_runtime.tasks.models import TaskRecord
from knowledge_runtime.tasks.store import TaskStore
from query.read.runtime import list_ingest_job_progress, summarize_job_progress


class JobProjector:
    def __init__(self, *, job_store: JobStore, task_store: TaskStore) -> None:
        self._job_store = job_store
        self._task_store = task_store

    def status(self, job_id: str) -> JobStatusResponse:
        runtime_record = self._job_store.get(job_id)
        record = (
            self._merge_persisted_progress(runtime_record)
            if runtime_record
            else self._persisted_record(job_id)
        )
        if record is None:
            return _missing_job(job_id)

        return _response_from_record(
            record,
            current_task=self._task_store.current_for_job(job_id),
        )

    def list(self, *, limit: int = 50) -> list[JobStatusResponse]:
        records_by_id = {
            record.job_id: record
            for record in self._persisted_records(limit=limit)
        }
        for runtime_record in self._job_store.list(limit=limit):
            # Runtime memory owns live task/stage metadata while the DB owns durable
            # graph progress. Prefer the runtime record when present, then merge DB
            # counts/phase into it.
            records_by_id[runtime_record.job_id] = self._merge_persisted_progress(
                runtime_record
            )

        records = sorted(
            records_by_id.values(),
            key=lambda record: record.updated_at,
            reverse=True,
        )[:limit]
        return [
            _response_from_record(
                record,
                current_task=self._task_store.current_for_job(record.job_id),
            )
            for record in records
        ]

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

    def _persisted_record(self, job_id: str) -> JobRecord | None:
        try:
            result = summarize_job_progress(job_id)
        except Exception:  # noqa: BLE001
            return None
        rows = result.get("rows") or []
        if not rows:
            return None
        return _record_from_persisted_row(rows[0])

    def _persisted_records(self, *, limit: int) -> list[JobRecord]:
        try:
            result = list_ingest_job_progress(limit=limit)
        except Exception:  # noqa: BLE001
            return []
        return [
            record
            for row in result.get("rows") or []
            if (record := _record_from_persisted_row(row)) is not None
        ]


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


def _record_from_persisted_row(row: dict[str, object]) -> JobRecord | None:
    job_props = _properties(row.get("job") or {})
    if not job_props:
        return None

    job_id = str(job_props.get("job_id") or job_props.get("id") or "").strip()
    if not job_id:
        return None

    phase = JobPhase.normalize(job_props.get("phase"))
    document_props = _document_properties(row)
    document_id = str(
        job_props.get("document_id") or document_props.get("id") or ""
    ).strip() or None
    errors = _strings(job_props.get("errors"))
    warnings = _strings(job_props.get("warnings"))
    status = JobStageStatus.FAILED if phase is JobPhase.FAILED else JobStageStatus.SUCCESS
    message = (
        errors[0]
        if errors
        else f"Persisted graph job phase is {phase.value}."
    )
    updated_at = _datetime_or_now(job_props.get("updated_at"))

    return JobRecord(
        job_id=job_id,
        file_name=str(
            document_props.get("file_name")
            or job_props.get("file_name")
            or "unknown"
        ),
        current_phase=phase,
        document_id=document_id,
        chunk_count=int(job_props.get("chunk_count") or row.get("chunk_count") or 0),
        candidate_count=int(
            job_props.get("candidate_count") or row.get("candidate_count") or 0
        ),
        pending_review_count=int(
            job_props.get("pending_review_count")
            or row.get("pending_review_count")
            or 0
        ),
        warning=warnings[0] if warnings else None,
        stages=[
            JobStage(
                phase=phase,
                status=status,
                message=message,
                error=message if status is JobStageStatus.FAILED else None,
            )
        ],
        updated_at=updated_at,
    )


def _properties(record: object) -> dict[str, object]:
    if not isinstance(record, dict):
        return {}
    nested = record.get("properties")
    if isinstance(nested, dict):
        return nested
    return record


def _document_properties(row: dict[str, object]) -> dict[str, object]:
    document_props = _properties(row.get("document") or {})
    if document_props:
        return document_props
    documents = row.get("documents")
    if isinstance(documents, list) and documents:
        return _properties(documents[0])
    return {}


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _datetime_or_now(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return datetime.now(UTC)
    return datetime.now(UTC)
