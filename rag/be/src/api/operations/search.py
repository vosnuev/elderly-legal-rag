from __future__ import annotations

from fastapi import APIRouter

from knowledge_runtime.schemas import SearchRequest, SearchResponse
from knowledge_runtime.service import knowledge_runtime

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def legacy_search(request: SearchRequest) -> SearchResponse:
    return knowledge_runtime.catalog.search(request)
