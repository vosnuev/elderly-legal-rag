from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit


def list_pending_review_candidates(
    document_id: str | None = None,
    job_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (candidate:RelationshipCandidate)
        WHERE coalesce(candidate.status, "pending_review") = "pending_review"
          AND ($job_id IS NULL OR candidate.job_id = $job_id)
        OPTIONAL MATCH (evidence)-[:EVIDENCES_RELATIONSHIP_CANDIDATE]->(candidate)
        WHERE $document_id IS NULL
          OR evidence.id = $document_id
          OR evidence.document_id = $document_id
          OR candidate.evidence_node_id = $document_id
          OR candidate.left_node = $document_id
          OR candidate.right_node = $document_id
        WITH DISTINCT candidate
        ORDER BY candidate.version ASC, candidate.id ASC
        RETURN candidate {
            .*,
            source_node: coalesce(candidate.source_node, candidate.left_node),
            target_node: coalesce(candidate.target_node, candidate.right_node),
            source_chunk_id: coalesce(candidate.source_chunk_id, candidate.evidence_node_id)
        } AS candidate
        LIMIT $limit
        """,
        {
            "document_id": document_id,
            "job_id": job_id,
            "limit": bounded_limit(limit),
        },
    )


def summarize_document_review_queue(document_id: str) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (document:Document {id: $document_id})
        OPTIONAL MATCH (document)-[:HAS_CHUNK]->(chunk:Chunk)
        WITH document, collect(DISTINCT chunk) AS chunks
        OPTIONAL MATCH (candidate:RelationshipCandidate)
        WHERE candidate.evidence_node_id IN [chunk IN chunks | chunk.id]
           OR candidate.left_node IN [chunk IN chunks | chunk.id]
           OR candidate.right_node IN [chunk IN chunks | chunk.id]
           OR candidate.evidence_node_id = document.id
           OR candidate.left_node = document.id
           OR candidate.right_node = document.id
        WITH document, chunks, collect(DISTINCT candidate) AS candidates
        RETURN document,
               size(chunks) AS chunk_count,
               size(candidates) AS candidate_count,
               size([candidate IN candidates WHERE coalesce(candidate.status, "pending_review") = "pending_review"]) AS pending_review_count,
               [candidate IN candidates | candidate.id] AS candidate_ids
        """,
        {"document_id": document_id},
    )
