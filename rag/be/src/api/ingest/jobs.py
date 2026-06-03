from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from fastapi.responses import StreamingResponse

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


@router.get("/api/ingest/jobs", response_model=list[JobStatusResponse])
def list_ingest_jobs(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[JobStatusResponse]:
    return knowledge_runtime.status.list(limit=limit)


@router.get("/ingest/status/{job_id}", response_model=JobStatusResponse)
def legacy_ingest_status(job_id: str) -> JobStatusResponse:
    return knowledge_runtime.status.get(job_id)


@router.get("/api/ingest/jobs/{job_id}", response_model=JobStatusResponse)
def get_ingest_job(job_id: str) -> JobStatusResponse:
    return knowledge_runtime.status.get(job_id)


@router.get("/api/ingest/jobs/{job_id}/events")
def stream_ingest_job_events(
    job_id: Annotated[str, Path(min_length=1)],
    last_event_id: Annotated[str, Query(min_length=1)] = "0-0",
) -> StreamingResponse:
    return knowledge_runtime.status.events(job_id, last_event_id=last_event_id)


@router.post("/api/ingest/jobs/{job_id}/start", response_model=JobStatusResponse)
async def start_ingest_job(job_id: str) -> JobStatusResponse:
    return await knowledge_runtime.documents.start_build(job_id)
