from __future__ import annotations

from typing import Any
from uuid import uuid4

from query.schema import RelationshipCandidateStatus, ReviewNoteNode
from query.utils import graph_properties
from query.write.core import write_query


def update_candidate_review_status(
    *,
    candidate_id: str,
    status: RelationshipCandidateStatus | str,
    reviewer: str,
) -> dict[str, Any]:
    return write_query(
        """
        MATCH (candidate:RelationshipCandidate {id: $candidate_id})
        SET candidate.status = $status,
            candidate.reviewed_by = $reviewer,
            candidate.reviewed_at = localDateTime()
        RETURN candidate
        """,
        {
            "candidate_id": candidate_id,
            "status": RelationshipCandidateStatus(status).value,
            "reviewer": reviewer,
        },
    )


def store_review_note(
    *,
    candidate_id: str,
    action: str,
    reviewer: str,
    note: str | None,
) -> dict[str, Any]:
    if not note or not note.strip():
        return {"stored": False}

    review_note = ReviewNoteNode(
        id=str(uuid4()),
        relationship_candidate_id=candidate_id,
        action=action,
        reviewer=reviewer,
        note=note.strip(),
    )
    return write_query(
        """
        MATCH (candidate:RelationshipCandidate {id: $candidate_id})
        CREATE (note:ReviewNote)
        SET note = $note,
            note.created_at = localDateTime()
        MERGE (candidate)-[:HAS_REVIEW_NOTE]->(note)
        RETURN note
        """,
        {
            "candidate_id": candidate_id,
            "note": graph_properties(review_note.model_dump()),
        },
    )
