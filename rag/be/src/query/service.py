from __future__ import annotations

from typing import Any

from query.client import MemgraphClient, get_memgraph_client
from query.guard import QueryValidationError, validate_read_query, validate_write_query
from query.instructions import GRAPH_SCHEMA_INSTRUCTIONS
from settings import settings


class MemgraphQueryService:
    def __init__(self, client: MemgraphClient | None = None) -> None:
        self._client = client or get_memgraph_client()

    def read_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        limit = self._bounded_limit(max_rows)
        validated = validate_read_query(query, max_rows=limit)
        result = self._client.execute_read(validated.query, parameters)
        result["warnings"] = list(validated.warnings)
        result["access"] = validated.access
        return result

    def vector_search(
        self,
        index_name: str,
        embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        limit = self._bounded_limit(top_k)
        query = """
        CALL vector_search.search($index_name, $limit, $embedding)
        YIELD node, similarity, distance
        RETURN node, similarity, distance
        ORDER BY similarity DESC
        """
        return self._client.execute_read(
            query,
            {
                "index_name": index_name,
                "limit": limit,
                "embedding": embedding,
            },
        )

    def keyword_search(self, keyword: str, top_k: int = 20) -> dict[str, Any]:
        limit = self._bounded_limit(top_k)
        query = """
        MATCH (n)
        WHERE toLower(toString(properties(n))) CONTAINS toLower($keyword)
        RETURN labels(n) AS labels, n AS node
        LIMIT $limit
        """
        return self._client.execute_read(
            query,
            {"keyword": keyword, "limit": limit},
        )

    def graph_traverse(
        self,
        node_id: str,
        id_property: str = "id",
        max_depth: int = 2,
        max_rows: int = 50,
    ) -> dict[str, Any]:
        depth = max(1, min(max_depth, 4))
        limit = self._bounded_limit(max_rows)
        property_name = self._safe_identifier(id_property)
        query = f"""
        MATCH path = (start {{{property_name}: $node_id}})-[*1..{depth}]-(neighbor)
        RETURN path
        LIMIT $limit
        """
        return self._client.execute_read(
            query,
            {"node_id": node_id, "limit": limit},
        )

    def schema_read(self) -> dict[str, Any]:
        labels = self._client.execute_read(
            """
            MATCH (n)
            UNWIND labels(n) AS label
            RETURN label, count(*) AS count
            ORDER BY label
            """
        )
        relationships = self._client.execute_read(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, count(*) AS count
            ORDER BY relationship_type
            """
        )
        vector_indexes = self._client.execute_read(
            "CALL vector_search.show_index_info() YIELD * RETURN *"
        )

        return {
            "instructions": GRAPH_SCHEMA_INSTRUCTIONS.strip(),
            "labels": labels["rows"],
            "relationship_types": relationships["rows"],
            "vector_indexes": vector_indexes["rows"],
            "query_limits": {
                "max_rows": settings.query_max_rows,
                "timeout_ms": settings.query_timeout_ms,
            },
        }

    def write_query(
        self,
        query: str,
        job_id: str,
        purpose: str,
        parameters: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        validated = validate_write_query(query, job_id=job_id, purpose=purpose)

        if dry_run:
            return {
                "dry_run": True,
                "access": validated.access,
                "query": validated.query,
                "parameters": parameters or {},
                "job_id": job_id,
                "purpose": purpose,
            }

        result = self._client.execute_write(validated.query, parameters)
        result["access"] = validated.access
        result["job_id"] = job_id
        result["purpose"] = purpose
        return result

    def upsert_document_graph(
        self,
        job_id: str,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        document_id = str(document.get("id") or "").strip()
        if not document_id:
            raise ValueError("document.id is required.")

        for chunk in chunks:
            if not str(chunk.get("id") or "").strip():
                raise ValueError("Each chunk requires id.")

        query = """
        MERGE (d:Document {id: $document_id})
        SET d += $document,
            d.last_ingest_job_id = $job_id
        WITH d
        UNWIND $chunks AS chunk
        MERGE (c:Chunk {id: chunk.id})
        SET c += chunk,
            c.document_id = $document_id,
            c.last_ingest_job_id = $job_id
        MERGE (d)-[:HAS_CHUNK]->(c)
        RETURN d.id AS document_id, count(c) AS chunk_count
        """

        if dry_run:
            return {
                "dry_run": True,
                "job_id": job_id,
                "document": document,
                "chunks": chunks,
                "query": query.strip(),
            }

        return self._client.execute_write(
            query,
            {
                "job_id": job_id,
                "document_id": document_id,
                "document": document,
                "chunks": chunks,
            },
        )

    def store_edge_candidates(
        self,
        job_id: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
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
            {"job_id": job_id, "candidates": candidates},
        )

    def probe_existing_context(
        self,
        keyword: str,
        top_k: int = 20,
    ) -> dict[str, Any]:
        return {
            "keyword_matches": self.keyword_search(keyword, top_k),
            "schema": self.schema_read(),
        }

    def review_edge_candidate(
        self,
        candidate_id: str,
        action: str,
        reviewer: str = "system",
    ) -> dict[str, Any]:
        normalized_action = action.strip().lower()
        if normalized_action not in {"approve", "reject", "retry"}:
            raise ValueError("action must be approve, reject, or retry.")

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
                "status": normalized_action,
                "reviewer": reviewer,
            },
        )

    def list_pending_edge_candidates(self, limit: int = 50) -> dict[str, Any]:
        bounded_limit = self._bounded_limit(limit)
        return self._client.execute_read(
            """
            MATCH (candidate:RelationshipCandidate)
            WHERE coalesce(candidate.status, "pending_review") = "pending_review"
            RETURN candidate
            LIMIT $limit
            """,
            {"limit": bounded_limit},
        )

    def _bounded_limit(self, value: int | None) -> int:
        if value is None:
            return settings.query_max_rows
        return max(1, min(value, settings.query_max_rows))

    def _safe_identifier(self, value: str) -> str:
        if not value.replace("_", "").isalnum() or value[0].isdigit():
            raise QueryValidationError(f"Unsafe Cypher identifier: {value}")
        return value
