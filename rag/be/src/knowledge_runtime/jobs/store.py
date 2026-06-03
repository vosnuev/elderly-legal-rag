"""Job state access boundary.

This module reads and writes operational job state without exposing storage
details to API routes or worker code.
"""

from __future__ import annotations

from threading import RLock

from knowledge_runtime.jobs.models import (
    JobPhase,
    JobRecord,
    JobStage,
    JobStageStatus,
    utc_now,
)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = RLock()

    def save(self, record: JobRecord) -> JobRecord:
        with self._lock:
            saved = record.model_copy(deep=True)
            saved.updated_at = utc_now()
            self._jobs[saved.job_id] = saved
            return saved.model_copy(deep=True)

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            return record.model_copy(deep=True) if record else None

    def list(self, *, limit: int = 50) -> list[JobRecord]:
        with self._lock:
            records = sorted(
                self._jobs.values(),
                key=lambda record: record.updated_at,
                reverse=True,
            )
            return [record.model_copy(deep=True) for record in records[:limit]]

    def create_stored(
        self,
        *,
        job_id: str,
        file_name: str,
        document_id: str,
        stages: list[JobStage],
    ) -> JobRecord:
        return self.save(
            JobRecord(
                job_id=job_id,
                file_name=file_name,
                current_phase=JobPhase.STORED,
                document_id=document_id,
                stages=[
                    *stages,
                    JobStage(
                        phase=JobPhase.STORED,
                        status=JobStageStatus.SUCCESS,
                        message="Stored original document.",
                    ),
                ],
            )
        )

    def mark_failed(
        self,
        *,
        job_id: str,
        file_name: str,
        message: str,
        stages: list[JobStage] | None = None,
    ) -> JobRecord:
        existing = self.get(job_id)
        base_stages = list(existing.stages if existing else stages or [])
        return self.save(
            JobRecord(
                job_id=job_id,
                file_name=existing.file_name if existing else file_name,
                current_phase=JobPhase.FAILED,
                document_id=existing.document_id if existing else None,
                chunk_count=existing.chunk_count if existing else 0,
                candidate_count=existing.candidate_count if existing else 0,
                pending_review_count=existing.pending_review_count if existing else 0,
                stages=[
                    *base_stages,
                    JobStage(
                        phase=JobPhase.FAILED,
                        status=JobStageStatus.FAILED,
                        message=message,
                        error=message,
                    ),
                ],
            )
        )

    def apply_pipeline_result(self, result: object) -> JobRecord | None:
        job_id = str(getattr(result, "job_id", "") or "")
        if not job_id:
            return None
        existing = self.get(job_id)
        if existing is None:
            return None

        phase = JobPhase.normalize(getattr(result, "phase", None))
        errors = [str(error) for error in getattr(result, "errors", []) or []]
        status = JobStageStatus.FAILED if phase is JobPhase.FAILED else JobStageStatus.SUCCESS
        message = errors[0] if errors else f"Runtime phase changed to {phase.value}."

        updated = existing.model_copy(deep=True)
        updated.current_phase = phase
        updated.document_id = str(getattr(result, "document_id", None) or updated.document_id or "")
        if not updated.document_id:
            updated.document_id = None
        updated.chunk_count = int(getattr(result, "chunk_count", updated.chunk_count) or 0)
        updated.candidate_count = int(
            getattr(result, "candidate_count", updated.candidate_count) or 0
        )
        updated.pending_review_count = int(
            getattr(result, "pending_review_count", updated.pending_review_count) or 0
        )
        updated.stages.append(
            JobStage(
                phase=phase,
                status=status,
                message=message,
                error=message if status is JobStageStatus.FAILED else None,
            )
        )
        return self.save(updated)
