from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from pipeline.schemas import (
    GraphIngestPhase,
    ReviewAction,
)


class GraphIngestState(TypedDict):
    job_id: str
    document_id: str
    chunk_ids: NotRequired[list[str]]
    edge_candidate_ids: NotRequired[list[str]]
    missing_chunk_ids: NotRequired[list[str]]
    phase: NotRequired[GraphIngestPhase]


class CandidateReviewActionState(TypedDict):
    candidate_id: str
    action: ReviewAction
    reviewer: str
    note: NotRequired[str | None]
    candidate: NotRequired[dict[str, Any]]
    edge_candidate_ids: NotRequired[list[str]]
    review_note: NotRequired[dict[str, Any] | None]
    memory_id: NotRequired[str | None]
    phase: NotRequired[GraphIngestPhase]
