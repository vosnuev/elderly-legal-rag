from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query

from ingestion.schemas import ReviewDecisionRequest
from ingestion.service import ingestion_service
from pipeline.schemas import IngestGraphResult

router = APIRouter(tags=["ingest-review"])


@router.get("/api/review/edge-candidates")
def list_edge_candidates(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    return ingestion_service.list_pending_edge_candidates(limit=limit)


@router.post("/api/review/edge-candidates/{candidate_id}/decision", response_model=IngestGraphResult)
def decide_edge_candidate(
    candidate_id: Annotated[str, Path(min_length=1)],
    request: ReviewDecisionRequest,
) -> IngestGraphResult:
    return ingestion_service.decide_edge_candidate(
        candidate_id=candidate_id,
        request=request,
    )
