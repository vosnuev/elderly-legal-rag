# 역할: memory update agent가 정리한 단일 Memory 문서를 versioned document로 갱신한다.
from __future__ import annotations

from typing import Any

from query.utils import db_generated_id_expression, graph_properties
from query.write.core import write_query

DEFAULT_MEMORY_SCOPE = "global"
DEFAULT_MEMORY_TITLE = "Candidate extraction memory"


def update_memory_document(
    *,
    content: str,
    scope: str = DEFAULT_MEMORY_SCOPE,
    title: str = DEFAULT_MEMORY_TITLE,
    update_summary: str = "",
    evidence_review_note_ids: list[str] | None = None,
    evidence_candidate_ids: list[str] | None = None,
    author: str = "memory_update_agent",
) -> dict[str, Any]:
    if not content.strip():
        return {"stored": False}

    review_note_ids = _unique_ids(evidence_review_note_ids)
    candidate_ids = _unique_ids(evidence_candidate_ids)
    result = write_query(
        f"""
        MERGE (memory:Memory {{scope: $scope}})
        ON CREATE SET memory.id = {db_generated_id_expression()},
                      memory.created_at = localDateTime(),
                      memory.version = 0,
                      memory.evidence_review_note_ids = [],
                      memory.evidence_relationship_candidate_ids = [],
                      memory.evidence_node_ids = []
        SET memory.content = $content,
            memory.title = $title,
            memory.status = "active",
            memory.author = $author,
            memory.version = coalesce(memory.version, 0) + 1,
            memory.evidence_review_note_ids = reduce(
                acc = [],
                item IN coalesce(memory.evidence_review_note_ids, []) + $review_note_ids |
                CASE
                    WHEN item IS NULL OR item IN acc THEN acc
                    ELSE acc + [item]
                END
            ),
            memory.evidence_relationship_candidate_ids = reduce(
                acc = [],
                item IN coalesce(memory.evidence_relationship_candidate_ids, []) + $candidate_ids |
                CASE
                    WHEN item IS NULL OR item IN acc THEN acc
                    ELSE acc + [item]
                END
            ),
            memory.metadata = $metadata,
            memory.updated_at = localDateTime()
        WITH memory
        UNWIND $review_note_ids AS review_note_id
        OPTIONAL MATCH (note:ReviewNote {{id: review_note_id}})
        WITH memory, [note IN collect(note) WHERE note IS NOT NULL] AS notes
        FOREACH (note IN notes |
            MERGE (note)-[:EVIDENCES_MEMORY]->(memory)
        )
        RETURN memory.id AS memory_id,
               memory.version AS version,
               memory.content AS content,
               memory.evidence_review_note_ids AS evidence_review_note_ids,
               memory.evidence_relationship_candidate_ids AS evidence_candidate_ids
        """,
        {
            "content": content.strip(),
            "scope": scope.strip() or DEFAULT_MEMORY_SCOPE,
            "title": title.strip() or DEFAULT_MEMORY_TITLE,
            "author": author,
            "review_note_ids": review_note_ids,
            "candidate_ids": candidate_ids,
            "metadata": graph_properties(
                {
                    "metadata": {
                        "format": "curated_markdown",
                        "last_update_summary": update_summary.strip(),
                    }
                }
            )["metadata"],
        },
    )
    return result


def _unique_ids(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        normalized = str(value).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result
