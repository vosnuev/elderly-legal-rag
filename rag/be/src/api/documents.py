from __future__ import annotations

from fastapi import APIRouter

from ingest_tasks.schemas import RagDocument, SearchRequest, SearchResponse
from ingest_tasks.service import ingest_task_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[RagDocument])
def list_documents() -> list[RagDocument]:
    return ingest_task_service.list_documents()


@router.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest) -> SearchResponse:
    return ingest_task_service.search(request)
