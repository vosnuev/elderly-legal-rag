from __future__ import annotations

from query.read import read_node_by_id
from query.utils import safe_identifier
from query.write import write_query


class ActualEdgeMaterializationService:
    def materialize(
        self,
        *,
        candidate_id: str,
        reviewer: str,
    ) -> dict[str, object]:
        candidate = read_node_by_id(candidate_id, label="RelationshipCandidate")
        source_node = str(candidate.get("source_node") or "").strip()
        target_node = str(candidate.get("target_node") or "").strip()
        if not source_node or not target_node:
            raise ValueError("RelationshipCandidate requires source_node and target_node.")

        relationship_type = safe_identifier(
            str(candidate.get("relationship_type") or "RELATED_TO")
        ).upper()
        query = f"""
        MATCH (candidate:RelationshipCandidate {{id: $candidate_id}})
        MATCH (source {{id: $source_node}})
        MATCH (target {{id: $target_node}})
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
        result = write_query(
            query,
            {
                "candidate_id": candidate_id,
                "source_node": source_node,
                "target_node": target_node,
                "source_chunk_id": str(candidate.get("source_chunk_id") or ""),
                "evidence_text": str(candidate.get("evidence_text") or ""),
                "rationale": str(candidate.get("rationale") or ""),
                "reviewer": reviewer,
            },
        )
        if not result["rows"]:
            raise ValueError("RelationshipCandidate source or target node was not found.")
        return result
