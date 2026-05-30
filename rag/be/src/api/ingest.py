from __future__ import annotations

from fastapi import APIRouter

from ingest_tasks.schemas import (
    CreateDocumentIngestJobRequest,
    FileIngestStatusResponse,
    RagIngestRequest,
)
from ingest_tasks.service import ingest_task_service

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=FileIngestStatusResponse)
def ingest(request: RagIngestRequest) -> FileIngestStatusResponse:
    return ingest_task_service.ingest_backend_file(request)


@router.get("/ingest/status/{job_id}", response_model=FileIngestStatusResponse)
def ingest_status(job_id: str) -> FileIngestStatusResponse:
    return ingest_task_service.get_status(job_id)


@router.post("/api/ingest/jobs", response_model=FileIngestStatusResponse)
def create_ingest_job(
    request: CreateDocumentIngestJobRequest,
) -> FileIngestStatusResponse:
    return ingest_task_service.create_text_job(request)


@router.get("/api/ingest/jobs/{job_id}", response_model=FileIngestStatusResponse)
def get_ingest_job(job_id: str) -> FileIngestStatusResponse:
    return ingest_task_service.get_status(job_id)


@router.post("/api/ingest/jobs/{job_id}/start", response_model=FileIngestStatusResponse)
def start_ingest_job(job_id: str) -> FileIngestStatusResponse:
    return ingest_task_service.start_graph_add(job_id)
