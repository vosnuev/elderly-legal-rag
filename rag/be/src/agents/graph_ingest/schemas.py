from __future__ import annotations

from pydantic import BaseModel, Field


class EdgeCandidate(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_span: str
    rationale: str
    status: str = "pending_review"
