from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.read.inspection.nodes import read_node_by_id
from query.utils import bounded_limit


def read_relationship_candidate(candidate_id: str) -> dict[str, Any]:
    return read_node_by_id(candidate_id, label="RelationshipCandidate")


def list_candidates_for_job(
    job_id: str,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (candidate:RelationshipCandidate {job_id: $job_id})
        WHERE $status IS NULL OR candidate.status = $status
        RETURN candidate
        ORDER BY candidate.version ASC, candidate.id ASC
        LIMIT $limit
        """,
        {
            "job_id": job_id,
            "status": status,
            "limit": bounded_limit(limit),
        },
    )


def list_candidates_for_document(
    document_id: str,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (document:Document {id: $document_id})
        OPTIONAL MATCH (document)-[:HAS_CHUNK]->(chunk:Chunk)
        WITH collect(chunk.id) + [document.id] AS document_node_ids
        MATCH (candidate:RelationshipCandidate)
        OPTIONAL MATCH (evidence)-[:EVIDENCES_RELATIONSHIP_CANDIDATE]->(candidate)
        WITH candidate, document_node_ids, collect(evidence.id) AS evidence_node_ids
        WHERE ($status IS NULL OR candidate.status = $status)
          AND (
            candidate.evidence_node_id IN document_node_ids
            OR candidate.left_node IN document_node_ids
            OR candidate.right_node IN document_node_ids
            OR any(evidence_id IN evidence_node_ids WHERE evidence_id IN document_node_ids)
          )
        RETURN candidate
        ORDER BY candidate.version ASC, candidate.id ASC
        LIMIT $limit
        """,
        {
            "document_id": document_id,
            "status": status,
            "limit": bounded_limit(limit),
        },
    )
