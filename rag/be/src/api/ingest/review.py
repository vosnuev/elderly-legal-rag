from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query

from ingest_tasks.service import ingest_task_service
from pipeline.schemas import IngestGraphResult, ReviewDecisionRequest

router = APIRouter(tags=["ingest-review"])


@router.get("/api/review/edge-candidates")
def list_edge_candidates(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    return ingest_task_service.list_pending_edge_candidates(limit=limit)


@router.post("/api/review/edge-candidates/{candidate_id}/decision", response_model=IngestGraphResult)
def decide_edge_candidate(
    candidate_id: Annotated[str, Path(min_length=1)],
    request: ReviewDecisionRequest,
) -> IngestGraphResult:
    return ingest_task_service.decide_edge_candidate(
        candidate_id=candidate_id,
        request=request,
    )
