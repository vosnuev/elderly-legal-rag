from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentMemoryNode(BaseModel):
    """agent가 재사용할 compact memory node.

    이 노드는 semantic knowledge graph의 지식 노드가 아니다. `ReviewNote`와
    `RelationshipCandidate` 같은 review evidence를 memory update agent가 필터링하고
    요약해서 만든 agent용 판단 근거이다.
    """

    id: str
    memory_kind: str = "review_preference"
    content: str
    title: str = ""
    scope: str = "global"
    evidence_review_note_ids: list[str] = Field(default_factory=list)
    evidence_relationship_candidate_ids: list[str] = Field(default_factory=list)
    evidence_node_ids: list[str] = Field(default_factory=list)
    author_agent: str = "memory_update_agent"
    status: str = "active"
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
