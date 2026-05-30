from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query

from agents.graph_ingest.orchestrator import GraphIngestOrchestrator
from agents.graph_ingest.schemas import IngestGraphResult, ReviewDecisionRequest
from query.service import get_memgraph_query_service

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/edge-candidates")
def list_edge_candidates(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    return get_memgraph_query_service().list_pending_edge_candidates(limit=limit)


@router.post("/edge-candidates/{candidate_id}/decision", response_model=IngestGraphResult)
def decide_edge_candidate(
    candidate_id: Annotated[str, Path(min_length=1)],
    request: ReviewDecisionRequest,
) -> IngestGraphResult:
    return GraphIngestOrchestrator().resume_review(
        candidate_id=candidate_id,
        action=request.action,
        reviewer=request.reviewer,
        note=request.note,
    )
