from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RelationshipCandidateStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RelationshipCandidateNode(BaseModel):
    """review 전 단계의 실제 DB node.

    `RelationshipCandidate`는 semantic content node가 아니라 review workflow artifact
    node이다. pending/approved/rejected 상태, user note, approved edge provenance를
    유지하기 위해 Memgraph에 실제 node로 저장한다.

    `job_id`는 이 candidate가 어떤 document ingest run에서 생성됐는지 묶는 runtime
    provenance field이며, 법령/조례/정책 의미를 나타내는 semantic property가 아니다.
    """

    id: str
    job_id: str
    left_node: str
    right_node: str
    relationship_type: str
    relationship_direction: Literal[
        "left_to_right",
        "right_to_left",
        "bidirectional",
    ] = "left_to_right"
    evidence_node_id: str | None = None
    evidence_text: str
    rationale: str
    status: RelationshipCandidateStatus = RelationshipCandidateStatus.PENDING_REVIEW
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewNoteNode(BaseModel):
    """특정 RelationshipCandidate에 붙는 reviewer feedback node.

    독립 knowledge node가 아니라 `RelationshipCandidate -[:HAS_REVIEW_NOTE]-> ReviewNote`
    형태의 review artifact이다. 장기 memory layer는 이 원본 note들을 직접 모두 읽지
    않고, memory update 단계가 단일 Memory 문서를 다시 정리해서 다음 agent가 읽는다.
    """

    id: str
    relationship_candidate_id: str
    action: str
    reviewer: str
    note: str
    metadata: dict[str, Any] = Field(default_factory=dict)
