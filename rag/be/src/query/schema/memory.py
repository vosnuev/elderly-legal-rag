from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryNode(BaseModel):
    """agent가 재사용할 단일 memory document node.

    이 노드는 semantic knowledge graph의 지식 노드가 아니다. `ReviewNote`와
    `RelationshipCandidate` 같은 review evidence를 근거로 계속 재정리되는 agent용
    판단 근거 문서이다.
    """

    id: str
    content: str
    title: str = ""
    scope: str = "global"
    evidence_review_note_ids: list[str] = Field(default_factory=list)
    evidence_relationship_candidate_ids: list[str] = Field(default_factory=list)
    evidence_node_ids: list[str] = Field(default_factory=list)
    author: str = "memory_node_service"
    status: str = "active"
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
