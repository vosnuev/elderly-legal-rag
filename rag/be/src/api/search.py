from __future__ import annotations

from fastapi import APIRouter

from ingest_tasks.schemas import SearchRequest, SearchResponse
from ingest_tasks.service import ingest_task_service

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def legacy_search(request: SearchRequest) -> SearchResponse:
    return ingest_task_service.search(request)
