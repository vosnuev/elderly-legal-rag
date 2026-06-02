from __future__ import annotations

from fastapi import APIRouter

from knowledge_runtime.schemas import DocumentSummary, SearchRequest, SearchResponse
from knowledge_runtime.service import knowledge_runtime

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    return knowledge_runtime.catalog.list_documents()


@router.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest) -> SearchResponse:
    return knowledge_runtime.catalog.search(request)
