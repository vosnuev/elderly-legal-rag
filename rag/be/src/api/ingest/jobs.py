from __future__ import annotations

from fastapi import APIRouter

from knowledge_runtime.schemas import (
    DocumentWorkRequest,
    JobStatusResponse,
    StoredFileWorkRequest,
)
from knowledge_runtime.service import knowledge_runtime

router = APIRouter(tags=["ingest-jobs"])


@router.post("/ingest", response_model=JobStatusResponse)
async def ingest(request: StoredFileWorkRequest) -> JobStatusResponse:
    return await knowledge_runtime.documents.create_from_file(request)


@router.post("/api/ingest/jobs", response_model=JobStatusResponse)
async def create_ingest_job(
    request: DocumentWorkRequest,
) -> JobStatusResponse:
    return await knowledge_runtime.documents.create_text(request)


@router.get("/ingest/status/{job_id}", response_model=JobStatusResponse)
def legacy_ingest_status(job_id: str) -> JobStatusResponse:
    return knowledge_runtime.status.get(job_id)


@router.get("/api/ingest/jobs/{job_id}", response_model=JobStatusResponse)
def get_ingest_job(job_id: str) -> JobStatusResponse:
    return knowledge_runtime.status.get(job_id)


@router.post("/api/ingest/jobs/{job_id}/start", response_model=JobStatusResponse)
async def start_ingest_job(job_id: str) -> JobStatusResponse:
    return await knowledge_runtime.documents.start_build(job_id)
