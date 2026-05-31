from __future__ import annotations

from typing import Any

from query.read.inspection import read_node_by_id
from query.schema import RelationshipCandidateStatus
from query.utils import safe_identifier
from query.write.core import write_query


def materialize_candidate_edge(
    *,
    candidate_id: str,
    reviewer: str,
) -> dict[str, Any]:
    candidate = read_node_by_id(candidate_id, label="RelationshipCandidate")
    left_node = str(candidate.get("left_node") or "").strip()
    right_node = str(candidate.get("right_node") or "").strip()
    if not left_node or not right_node:
        raise ValueError("RelationshipCandidate requires left_node and right_node.")

    relationship_type = safe_identifier(
        str(candidate.get("relationship_type") or "RELATED_TO")
    ).upper()
    relationship_direction = str(
        candidate.get("relationship_direction") or "left_to_right"
    ).strip()
    query = _materialize_query(relationship_type, relationship_direction)
    result = write_query(
        query,
        {
            "candidate_id": candidate_id,
            "left_node": left_node,
            "right_node": right_node,
            "relationship_direction": relationship_direction,
            "evidence_node_id": str(candidate.get("evidence_node_id") or ""),
            "evidence_text": str(candidate.get("evidence_text") or ""),
            "rationale": str(candidate.get("rationale") or ""),
            "reviewer": reviewer,
            "approved_status": RelationshipCandidateStatus.APPROVED.value,
        },
    )
    if not result["rows"]:
        raise ValueError("RelationshipCandidate left or right node was not found.")
    return result


def _materialize_query(relationship_type: str, relationship_direction: str) -> str:
    if relationship_direction == "right_to_left":
        edge_merge = f"MERGE (right)-[edge:{relationship_type}]->(left)"
    elif relationship_direction == "bidirectional":
        edge_merge = f"""
        MERGE (left)-[left_edge:{relationship_type}]->(right)
        MERGE (right)-[right_edge:{relationship_type}]->(left)
        WITH candidate, left_edge, right_edge
        SET left_edge.candidate_id = $candidate_id,
            left_edge.evidence_node_id = $evidence_node_id,
            left_edge.evidence_text = $evidence_text,
            left_edge.rationale = $rationale,
            left_edge.relationship_direction = $relationship_direction,
            left_edge.materialized_by = $reviewer,
            left_edge.materialized_at = localDateTime(),
            right_edge.candidate_id = $candidate_id,
            right_edge.evidence_node_id = $evidence_node_id,
            right_edge.evidence_text = $evidence_text,
            right_edge.rationale = $rationale,
            right_edge.relationship_direction = $relationship_direction,
            right_edge.materialized_by = $reviewer,
            right_edge.materialized_at = localDateTime()
        """
        return f"""
        MATCH (candidate:RelationshipCandidate {{id: $candidate_id}})
        MATCH (left {{id: $left_node}})
        MATCH (right {{id: $right_node}})
        {edge_merge}
        SET candidate.status = $approved_status,
            candidate.materialized = true,
            candidate.reviewed_by = $reviewer,
            candidate.reviewed_at = localDateTime()
        RETURN [left_edge, right_edge] AS edges, candidate
        """
    else:
        edge_merge = f"MERGE (left)-[edge:{relationship_type}]->(right)"

    return f"""
    MATCH (candidate:RelationshipCandidate {{id: $candidate_id}})
    MATCH (left {{id: $left_node}})
    MATCH (right {{id: $right_node}})
    {edge_merge}
    SET edge.candidate_id = $candidate_id,
        edge.evidence_node_id = $evidence_node_id,
        edge.evidence_text = $evidence_text,
        edge.rationale = $rationale,
        edge.relationship_direction = $relationship_direction,
        edge.materialized_by = $reviewer,
        edge.materialized_at = localDateTime()
    SET candidate.status = $approved_status,
        candidate.materialized = true,
        candidate.reviewed_by = $reviewer,
        candidate.reviewed_at = localDateTime()
    RETURN edge, candidate
    """
