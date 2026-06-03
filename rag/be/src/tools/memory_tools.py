# 역할: memory_update_agent가 정리한 Memory 문서 전체를 저장하는 write tool wrapper이다.
from __future__ import annotations

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from query.write import update_memory_document


class WriteMemoryDocumentToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        min_length=1,
        description="Full updated Memory markdown document content.",
    )
    scope: str = Field(
        default="global",
        min_length=1,
        description="Memory document scope. Use global for the shared agent memory.",
    )
    title: str = Field(
        default="Candidate extraction memory",
        min_length=1,
        description="Memory document title.",
    )
    update_summary: str = Field(
        default="",
        description="Short Korean summary of what changed in this memory update.",
    )
    evidence_review_note_ids: list[str] = Field(
        default_factory=list,
        description="ReviewNote ids that support this memory update.",
    )
    evidence_candidate_ids: list[str] = Field(
        default_factory=list,
        description="RelationshipCandidate ids that support this memory update.",
    )


@tool(args_schema=WriteMemoryDocumentToolInput)
def write_memory_document_tool(
    content: str,
    scope: str = "global",
    title: str = "Candidate extraction memory",
    update_summary: str = "",
    evidence_review_note_ids: list[str] | None = None,
    evidence_candidate_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Replace the shared Memory document with a curated updated version."""
    return update_memory_document(
        content=content,
        scope=scope,
        title=title,
        update_summary=update_summary,
        evidence_review_note_ids=evidence_review_note_ids or [],
        evidence_candidate_ids=evidence_candidate_ids or [],
        author="memory_update_agent",
    )
