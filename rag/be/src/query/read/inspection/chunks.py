from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit, node_properties


def read_chunk_by_id(chunk_id: str) -> dict[str, Any]:
    result = get_memgraph_bolt_client().execute_read(
        """
        MATCH (chunk:Chunk {id: $chunk_id})
        RETURN chunk
        LIMIT 1
        """,
        {"chunk_id": chunk_id},
    )
    if not result["rows"]:
        raise ValueError(f"Chunk not found: {chunk_id}")
    return node_properties(result["rows"][0]["chunk"])


def list_chunks_for_document(
    document_id: str,
    limit: int = 500,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)
        RETURN chunk
        ORDER BY chunk.chunk_index ASC, chunk.id ASC
        LIMIT $limit
        """,
        {
            "document_id": document_id,
            "limit": bounded_limit(limit),
        },
    )


def list_unembedded_chunks(
    document_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (chunk:Chunk)
        WHERE ($document_id IS NULL OR chunk.document_id = $document_id)
          AND coalesce(chunk.embedding_status, "pending") <> "embedded"
        RETURN chunk
        ORDER BY chunk.chunk_index ASC, chunk.id ASC
        LIMIT $limit
        """,
        {
            "document_id": document_id,
            "limit": bounded_limit(limit),
        },
    )
