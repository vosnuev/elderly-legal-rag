from __future__ import annotations

from fastapi import APIRouter

from ingestion.schemas import SearchRequest, SearchResponse
from ingestion.service import ingestion_service

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def legacy_search(request: SearchRequest) -> SearchResponse:
    return ingestion_service.search(request)
