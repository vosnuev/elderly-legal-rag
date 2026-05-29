from __future__ import annotations

from typing import Any

from langchain.tools import tool
from langchain_core.tools import BaseTool

from query.service import MemgraphQueryService


def get_graph_ingest_tools(
    service: MemgraphQueryService | None = None,
) -> list[BaseTool]:
    query_service = service or MemgraphQueryService()

    @tool
    def memgraph_read_query(
        query: str,
        parameters: dict[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        """Execute a validated read-only Cypher query against Memgraph."""
        return query_service.read_query(query, parameters, max_rows)

    @tool
    def memgraph_write_query(
        query: str,
        job_id: str,
        purpose: str,
        parameters: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Execute a validated internal write Cypher query for ingest jobs."""
        return query_service.write_query(query, job_id, purpose, parameters, dry_run)

    @tool
    def memgraph_vector_search(
        index_name: str,
        embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Run Memgraph vector_search.search over a vector index."""
        return query_service.vector_search(index_name, embedding, top_k)

    @tool
    def memgraph_keyword_search(keyword: str, top_k: int = 20) -> dict[str, Any]:
        """Search text-bearing graph nodes with a bounded keyword query."""
        return query_service.keyword_search(keyword, top_k)

    @tool
    def memgraph_graph_traverse(
        node_id: str,
        id_property: str = "id",
        max_depth: int = 2,
        max_rows: int = 50,
    ) -> dict[str, Any]:
        """Traverse a bounded graph neighborhood from a node id property."""
        return query_service.graph_traverse(node_id, id_property, max_depth, max_rows)

    @tool
    def memgraph_schema_read() -> dict[str, Any]:
        """Read graph labels, relationship types, vector indexes, and instructions."""
        return query_service.schema_read()

    @tool
    def memgraph_upsert_document_graph(
        job_id: str,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Idempotently upsert a document and chunks during ingest."""
        return query_service.upsert_document_graph(job_id, document, chunks, dry_run)

    @tool
    def memgraph_store_edge_candidates(
        job_id: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Store pending low-confidence relationship candidates for review."""
        return query_service.store_edge_candidates(job_id, candidates)

    @tool
    def memgraph_probe_existing_context(
        keyword: str,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """Probe existing graph context for new document placement."""
        return query_service.probe_existing_context(keyword, top_k)

    @tool
    def memgraph_review_edge_candidate(
        candidate_id: str,
        action: str,
        reviewer: str = "system",
    ) -> dict[str, Any]:
        """Approve, reject, or retry a stored relationship candidate."""
        return query_service.review_edge_candidate(candidate_id, action, reviewer)

    return [
        memgraph_read_query,
        memgraph_write_query,
        memgraph_vector_search,
        memgraph_keyword_search,
        memgraph_graph_traverse,
        memgraph_schema_read,
        memgraph_upsert_document_graph,
        memgraph_store_edge_candidates,
        memgraph_probe_existing_context,
        memgraph_review_edge_candidate,
    ]
