# 역할: 자유형 Memory 문서를 append 방식으로 업데이트하고 필요한 provenance link를 남기는 write query이다.
from __future__ import annotations

from typing import Any

from query.utils import db_generated_id_expression, graph_properties
from query.write.core import write_query

DEFAULT_MEMORY_SCOPE = "global"
DEFAULT_MEMORY_TITLE = "Reviewer feedback memory"


def append_memory_entry(
    *,
    entry: str,
    scope: str = DEFAULT_MEMORY_SCOPE,
    title: str = DEFAULT_MEMORY_TITLE,
    source_review_note_id: str | None = None,
    source_candidate_id: str | None = None,
    author: str = "memory_node_service",
) -> dict[str, Any]:
    if not entry.strip():
        return {"stored": False}

    query = f"""
    OPTIONAL MATCH (note:ReviewNote {{id: $source_review_note_id}})
    WITH note
    WHERE $source_review_note_id IS NULL OR note IS NOT NULL
    WITH note, coalesce(note.relationship_candidate_id, $source_candidate_id) AS candidate_id
    MERGE (memory:Memory {{scope: $scope}})
    ON CREATE SET memory.id = {db_generated_id_expression()},
                  memory.title = $title,
                  memory.content = "",
                  memory.status = "active",
                  memory.version = 0,
                  memory.evidence_review_note_ids = [],
                  memory.evidence_relationship_candidate_ids = [],
                  memory.evidence_node_ids = [],
                  memory.metadata = $metadata,
                  memory.created_at = localDateTime()
    SET memory.content = CASE
            WHEN coalesce(memory.content, "") = "" THEN $entry
            ELSE memory.content + $separator + $entry
        END,
        memory.title = coalesce($title, memory.title),
        memory.author = $author,
        memory.status = "active",
        memory.version = coalesce(memory.version, 0) + 1,
        memory.evidence_review_note_ids = CASE
            WHEN note IS NULL THEN coalesce(memory.evidence_review_note_ids, [])
            WHEN note.id IN coalesce(memory.evidence_review_note_ids, []) THEN coalesce(memory.evidence_review_note_ids, [])
            ELSE coalesce(memory.evidence_review_note_ids, []) + [note.id]
        END,
        memory.evidence_relationship_candidate_ids = CASE
            WHEN candidate_id IS NULL THEN coalesce(memory.evidence_relationship_candidate_ids, [])
            WHEN candidate_id IN coalesce(memory.evidence_relationship_candidate_ids, []) THEN coalesce(memory.evidence_relationship_candidate_ids, [])
            ELSE coalesce(memory.evidence_relationship_candidate_ids, []) + [candidate_id]
        END,
        memory.updated_at = localDateTime()
    FOREACH (_ IN CASE WHEN note IS NULL THEN [] ELSE [1] END |
        MERGE (note)-[:EVIDENCES_MEMORY]->(memory)
    )
    RETURN memory.id AS memory_id,
           note.id AS source_review_note_id,
           candidate_id AS source_candidate_id,
           memory.version AS version,
           memory.content AS content
    """
    result = write_query(
        query,
        {
            "entry": entry.strip(),
            "separator": "\n\n",
            "scope": scope,
            "title": title,
            "source_review_note_id": _optional_id(source_review_note_id),
            "source_candidate_id": _optional_id(source_candidate_id),
            "author": author,
            "metadata": graph_properties(
                {"metadata": {"format": "append_only_markdown"}}
            )["metadata"],
        },
    )
    if source_review_note_id and not result.get("rows"):
        raise ValueError(f"ReviewNote not found: {source_review_note_id}")
    return result


def _optional_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
