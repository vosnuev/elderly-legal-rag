# 역할: review graph 마지막에 job 단위 ReviewNote를 종합해 Memory 문서를 갱신하는 node service이다.
from __future__ import annotations

from typing import Any

from pipeline.sub_agents.memory_update_agent import MemoryUpdateAgent
from query.read.inspection import list_memory, list_review_notes_for_job
from query.utils import node_properties
from tools.agent_output_sanitize import sanitize_agent_tool_output


class MemoryNodeService:
    def __init__(self, memory_update_agent: MemoryUpdateAgent | None = None) -> None:
        self._memory_update_agent = memory_update_agent or MemoryUpdateAgent()

    def update_from_job_review_notes(
        self,
        *,
        job_id: str,
    ) -> dict[str, Any]:
        review_context = _review_context_for_job(job_id)
        if not review_context:
            return {"stored": False}

        memory = self._memory_update_agent.run(
            job_id=job_id,
            current_memory=_current_memory(),
            review_context=review_context,
        )
        return {
            "rows": [
                {
                    "memory_id": memory.get("id"),
                    "memory": memory,
                    "version": memory.get("version"),
                }
            ]
        }


def _current_memory() -> dict[str, Any]:
    result = list_memory(scope="global", status="active", limit=1)
    rows = result.get("rows") or []
    if not rows:
        return {
            "scope": "global",
            "title": "Candidate extraction memory",
            "content": "",
            "version": 0,
            "evidence_review_note_ids": [],
            "evidence_relationship_candidate_ids": [],
        }
    return node_properties(rows[0].get("memory"))


def _review_context_for_job(job_id: str) -> list[dict[str, Any]]:
    result = list_review_notes_for_job(job_id=job_id, limit=100)
    contexts: list[dict[str, Any]] = []
    for row in result.get("rows") or []:
        note = _node_context(row.get("note"))
        if not note:
            continue
        contexts.append(
            sanitize_agent_tool_output(
                {
                    "candidate_id": row.get("candidate_id"),
                    "review_note": note,
                    "candidate": _node_context(row.get("candidate")),
                    "left_node": _node_context(row.get("left")),
                    "right_node": _node_context(row.get("right")),
                    "evidence_node": _node_context(row.get("evidence")),
                }
            )
        )
    return contexts


def _node_context(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    try:
        properties = node_properties(value)
    except ValueError:
        return None
    labels = value.get("labels")
    return {
        "labels": labels if isinstance(labels, list) else [],
        "properties": properties,
    }
