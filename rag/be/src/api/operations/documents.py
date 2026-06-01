from __future__ import annotations

from fastapi import APIRouter

from ingestion.schemas import RagDocument, SearchRequest, SearchResponse
from ingestion.service import ingestion_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[RagDocument])
def list_documents() -> list[RagDocument]:
    return ingestion_service.list_documents()


@router.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest) -> SearchResponse:
    return ingestion_service.search(request)
