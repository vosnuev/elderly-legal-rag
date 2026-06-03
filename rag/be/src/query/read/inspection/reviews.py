from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit


def list_review_notes_for_candidate(
    candidate_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (:RelationshipCandidate {id: $candidate_id})-[:HAS_REVIEW_NOTE]->(note:ReviewNote)
        RETURN note
        ORDER BY note.created_at DESC, note.id DESC
        LIMIT $limit
        """,
        {
            "candidate_id": candidate_id,
            "limit": bounded_limit(limit),
        },
    )


def list_review_notes_for_job(
    job_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (candidate:RelationshipCandidate {job_id: $job_id})-[:HAS_REVIEW_NOTE]->(note:ReviewNote)
        OPTIONAL MATCH (left {id: candidate.left_node})
        OPTIONAL MATCH (right {id: candidate.right_node})
        OPTIONAL MATCH (evidence {id: candidate.evidence_node_id})
        RETURN candidate.id AS candidate_id,
               candidate,
               note,
               left,
               right,
               evidence
        ORDER BY note.created_at DESC, note.id DESC
        LIMIT $limit
        """,
        {
            "job_id": job_id,
            "limit": bounded_limit(limit),
        },
    )
