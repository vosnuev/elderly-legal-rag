from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.utils import bounded_limit, graph_properties, safe_identifier


class RelationshipCandidateRepository:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def store_edge_candidates(
        self,
        job_id: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not candidates:
            return {"stored_count": 0}
        query = """
        UNWIND $candidates AS candidate
        MERGE (rc:RelationshipCandidate {id: candidate.id})
        SET rc += candidate,
            rc.job_id = $job_id,
            rc.status = coalesce(candidate.status, "pending_review")
        RETURN count(rc) AS stored_count
        """
        return self._client.execute_write(
            query,
            {
                "job_id": job_id,
                "candidates": [graph_properties(candidate) for candidate in candidates],
            },
        )

    def review_edge_candidate(
        self,
        candidate_id: str,
        action: str,
        reviewer: str = "system",
    ) -> dict[str, Any]:
        normalized_action = action.strip().lower()
        if normalized_action not in {"approve", "reject", "retry"}:
            raise ValueError("action must be approve, reject, or retry.")
        status = {
            "approve": "approved",
            "reject": "rejected",
            "retry": "retry",
        }[normalized_action]

        query = """
        MATCH (rc:RelationshipCandidate {id: $candidate_id})
        SET rc.status = $status,
            rc.reviewed_by = $reviewer,
            rc.reviewed_at = localDateTime()
        RETURN rc
        """
        return self._client.execute_write(
            query,
            {
                "candidate_id": candidate_id,
                "status": status,
                "reviewer": reviewer,
            },
        )

    def get_edge_candidate(self, candidate_id: str) -> dict[str, Any]:
        result = self._client.execute_read(
            """
            MATCH (candidate:RelationshipCandidate {id: $candidate_id})
            RETURN candidate
            LIMIT 1
            """,
            {"candidate_id": candidate_id},
        )
        if not result["rows"]:
            raise ValueError(f"RelationshipCandidate not found: {candidate_id}")
        return result["rows"][0]["candidate"]

    def materialize_edge_candidate(
        self,
        candidate_id: str,
        reviewer: str,
    ) -> dict[str, Any]:
        candidate = self.get_edge_candidate(candidate_id)
        properties = candidate.get("properties", candidate)
        relationship_type = safe_identifier(
            str(properties.get("relationship_type") or "RELATED_TO")
        ).upper()

        query = f"""
        MATCH (candidate:RelationshipCandidate {{id: $candidate_id}})
        MERGE (source:Entity {{id: $source_node}})
        SET source.name = coalesce(source.name, $source_node)
        MERGE (target:Entity {{id: $target_node}})
        SET target.name = coalesce(target.name, $target_node)
        MERGE (source)-[edge:{relationship_type}]->(target)
        SET edge.candidate_id = $candidate_id,
            edge.source_chunk_id = $source_chunk_id,
            edge.evidence_text = $evidence_text,
            edge.rationale = $rationale,
            edge.materialized_by = $reviewer,
            edge.materialized_at = localDateTime()
        SET candidate.status = "approved",
            candidate.materialized = true,
            candidate.reviewed_by = $reviewer,
            candidate.reviewed_at = localDateTime()
        RETURN edge, candidate
        """
        return self._client.execute_write(
            query,
            {
                "candidate_id": candidate_id,
                "source_node": str(properties.get("source_node") or ""),
                "target_node": str(properties.get("target_node") or ""),
                "source_chunk_id": str(properties.get("source_chunk_id") or ""),
                "evidence_text": str(properties.get("evidence_text") or ""),
                "rationale": str(properties.get("rationale") or ""),
                "reviewer": reviewer,
            },
        )

    def list_pending_edge_candidates(self, limit: int = 50) -> dict[str, Any]:
        return self._client.execute_read(
            """
            MATCH (candidate:RelationshipCandidate)
            WHERE coalesce(candidate.status, "pending_review") = "pending_review"
            RETURN candidate
            LIMIT $limit
            """,
            {"limit": bounded_limit(limit)},
        )
