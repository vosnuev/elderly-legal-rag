from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from pipeline.schemas import (
    FeedbackJudgeResult,
    GraphChunk,
    GraphIngestPhase,
    RegisteredDocument,
    RelationshipCandidate,
    ReviewAction,
)


class GraphIngestState(TypedDict):
    job_id: str
    document_id: str
    document: NotRequired[RegisteredDocument]
    chunks: NotRequired[list[GraphChunk]]
    candidates: NotRequired[list[RelationshipCandidate]]
    feedback: NotRequired[FeedbackJudgeResult]
    phase: NotRequired[GraphIngestPhase]
    retry_count: NotRequired[int]
    warnings: NotRequired[list[str]]
    errors: NotRequired[list[str]]


class CandidateReviewActionState(TypedDict):
    candidate_id: str
    action: ReviewAction
    reviewer: str
    note: NotRequired[str | None]
    candidate: NotRequired[dict[str, Any]]
    candidates: NotRequired[list[RelationshipCandidate]]
    phase: NotRequired[GraphIngestPhase]
    warnings: NotRequired[list[str]]
    errors: NotRequired[list[str]]
