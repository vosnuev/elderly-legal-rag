from __future__ import annotations

from fastapi import APIRouter

from ingestion.schemas import (
    CreateDocumentIngestJobRequest,
    FileIngestStatusResponse,
    RagIngestRequest,
)
from ingestion.service import ingestion_service

router = APIRouter(tags=["ingest-jobs"])


@router.post("/ingest", response_model=FileIngestStatusResponse)
def ingest(request: RagIngestRequest) -> FileIngestStatusResponse:
    return ingestion_service.ingest_backend_file(request)


@router.post("/api/ingest/jobs", response_model=FileIngestStatusResponse)
def create_ingest_job(
    request: CreateDocumentIngestJobRequest,
) -> FileIngestStatusResponse:
    return ingestion_service.create_text_job(request)


@router.get("/ingest/status/{job_id}", response_model=FileIngestStatusResponse)
def legacy_ingest_status(job_id: str) -> FileIngestStatusResponse:
    return ingestion_service.get_status(job_id)


@router.get("/api/ingest/jobs/{job_id}", response_model=FileIngestStatusResponse)
def get_ingest_job(job_id: str) -> FileIngestStatusResponse:
    return ingestion_service.get_status(job_id)


@router.post("/api/ingest/jobs/{job_id}/start", response_model=FileIngestStatusResponse)
def start_ingest_job(job_id: str) -> FileIngestStatusResponse:
    return ingestion_service.start_graph_add(job_id)
