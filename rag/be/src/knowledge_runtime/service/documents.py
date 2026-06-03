"""Document work command service."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from knowledge_runtime.documents.registry import DocumentRegistry
from knowledge_runtime.jobs.models import JobPhase, JobStage, JobStageStatus
from knowledge_runtime.jobs.projector import JobProjector
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.schemas import (
    DocumentWorkRequest,
    JobStatusResponse,
    StoredFileWorkRequest,
    SUPPORTED_DOCUMENT_SUFFIXES,
)
from knowledge_runtime.tasks.submitter import TaskSubmitter
from query.write import upsert_ingest_job_progress


class DocumentWorkService:
    def __init__(
        self,
        *,
        registry: DocumentRegistry,
        job_store: JobStore,
        submitter: TaskSubmitter,
        projector: JobProjector,
    ) -> None:
        self._registry = registry
        self._job_store = job_store
        self._submitter = submitter
        self._projector = projector

    async def create_text(self, request: DocumentWorkRequest) -> JobStatusResponse:
        job_id = str(uuid4())
        stages = [
            JobStage(
                phase=JobPhase.RECEIVED,
                status=JobStageStatus.SUCCESS,
                message="Received text document payload.",
            )
        ]
        return await self._create_from_content(
            job_id=job_id,
            file_name=request.file_name,
            raw_content=request.content,
            content_type=request.content_type,
            source_path=None,
            stages=stages,
        )

    async def create_from_file(self, request: StoredFileWorkRequest) -> JobStatusResponse:
        source_path = Path(request.stored_path)
        stages = [
            JobStage(
                phase=JobPhase.RECEIVED,
                status=JobStageStatus.SUCCESS,
                message="Received backend upload file path.",
                path=str(source_path),
            )
        ]
        if not source_path.exists() or not source_path.is_file():
            failed = self._job_store.mark_failed(
                job_id=request.job_id,
                file_name=request.file_name,
                stages=stages,
                message="Backend upload file path does not exist.",
            )
            return self._projector.status(failed.job_id)

        suffix = source_path.suffix.lower()
        if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
            failed = self._job_store.mark_failed(
                job_id=request.job_id,
                file_name=request.file_name,
                stages=stages,
                message=f"Unsupported input suffix: {suffix or 'none'}",
            )
            return self._projector.status(failed.job_id)

        raw_content = source_path.read_text(encoding="utf-8")
        stages.append(
            JobStage(
                phase=JobPhase.VALIDATED,
                status=JobStageStatus.SUCCESS,
                message="File path and suffix validation completed.",
            )
        )
        return await self._create_from_content(
            job_id=request.job_id,
            file_name=request.file_name,
            raw_content=raw_content,
            content_type=request.content_type,
            source_path=str(source_path),
            stages=stages,
        )

    async def start_build(self, job_id: str) -> JobStatusResponse:
        record = self._job_store.get(job_id)
        if record is None:
            return self._projector.status(job_id)
        if not record.document_id:
            failed = self._job_store.mark_failed(
                job_id=job_id,
                file_name=record.file_name,
                message="No document_id was stored for this job.",
            )
            return self._projector.status(failed.job_id)

        await self._submitter.submit_build(
            job_id=record.job_id,
            document_id=record.document_id,
        )
        return self._projector.status(record.job_id)

    async def _create_from_content(
        self,
        *,
        job_id: str,
        file_name: str,
        raw_content: str,
        content_type: str | None,
        source_path: str | None,
        stages: list[JobStage],
    ) -> JobStatusResponse:
        try:
            document = self._registry.register_text(
                job_id=job_id,
                file_name=file_name,
                raw_content=raw_content,
                source_path=source_path,
                content_type=content_type,
            )
        except Exception as exc:  # noqa: BLE001
            failed = self._job_store.mark_failed(
                job_id=job_id,
                file_name=file_name,
                stages=stages,
                message=str(exc),
            )
            return self._projector.status(failed.job_id)

        self._job_store.create_stored(
            job_id=job_id,
            file_name=file_name,
            document_id=document.document_id,
            stages=stages,
        )
        # Persist the durable job seed immediately. JobStore/TaskStore are process
        # overlays, so FE job lists must be able to recover this row after restart.
        upsert_ingest_job_progress(
            job_id=job_id,
            phase=JobPhase.STORED.value,
            document_id=document.document_id,
            chunk_count=0,
            candidate_count=0,
            pending_review_count=0,
        )
        await self._submitter.submit_build(
            job_id=job_id,
            document_id=document.document_id,
        )
        return self._projector.status(job_id)
