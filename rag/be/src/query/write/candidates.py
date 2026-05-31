from __future__ import annotations

from typing import Any
from uuid import uuid4

from query.schema import RelationshipCandidateNode, RelationshipCandidateStatus
from query.utils import graph_properties
from query.write.core import write_query


def write_relationship_candidates(
    candidates: list[RelationshipCandidateNode | dict[str, Any]],
) -> dict[str, Any]:
    records = [_candidate_record(candidate) for candidate in candidates]
    if not records:
        return {"stored_count": 0, "edge_candidate_ids": []}

    result = write_query(
        """
        UNWIND $candidates AS candidate
        MATCH (left {id: candidate.left_node})
        MATCH (right {id: candidate.right_node})
        OPTIONAL MATCH (evidence {id: candidate.evidence_node_id})
        MERGE (rc:RelationshipCandidate {id: candidate.id})
        ON CREATE SET rc.created_at = localDateTime()
        SET rc += candidate,
            rc.job_id = candidate.job_id,
            rc.status = coalesce(candidate.status, $pending_review_status),
            rc.updated_at = localDateTime()
        FOREACH (_ IN CASE WHEN evidence IS NULL THEN [] ELSE [1] END |
            MERGE (evidence)-[:EVIDENCES_RELATIONSHIP_CANDIDATE]->(rc)
        )
        MERGE (left)-[:CANDIDATE_LEFT]->(rc)
        MERGE (rc)-[:CANDIDATE_RIGHT]->(right)
        RETURN count(rc) AS stored_count,
               collect(rc.id) AS edge_candidate_ids,
               count(evidence) AS linked_evidence_count,
               count(left) AS linked_left_count,
               count(right) AS linked_right_count
        """,
        {
            "candidates": [
                graph_properties(candidate)
                for candidate in records
            ],
            "pending_review_status": RelationshipCandidateStatus.PENDING_REVIEW.value,
        },
    )
    _require_expected_write_count(result, len(records), "RelationshipCandidate")
    return result


def write_candidate_revisions(
    *,
    previous_candidate_id: str,
    candidates: list[RelationshipCandidateNode | dict[str, Any]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        record = _candidate_record(candidate)
        record["previous_candidate_id"] = previous_candidate_id
        records.append(record)
    return write_relationship_candidates(records)


def _candidate_record(
    candidate: RelationshipCandidateNode | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(candidate, RelationshipCandidateNode):
        source = candidate.model_dump()
    else:
        source = dict(candidate)
    source.setdefault("id", str(uuid4()))
    source.setdefault("status", RelationshipCandidateStatus.PENDING_REVIEW)
    return RelationshipCandidateNode.model_validate(source).model_dump(mode="json")


def _require_expected_write_count(
    result: dict[str, Any],
    expected_count: int,
    label: str,
) -> None:
    if not result.get("rows"):
        raise ValueError(f"{label} write returned no rows.")
    stored_count = int(result["rows"][0].get("stored_count") or 0)
    if stored_count != expected_count:
        raise ValueError(
            f"{label} write stored {stored_count} rows; expected {expected_count}."
        )
