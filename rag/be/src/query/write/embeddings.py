from __future__ import annotations

from typing import Any

from query.write.core import write_query


def update_chunk_embedding(
    *,
    job_id: str,
    chunk_id: str,
    embedding: list[float],
    embedding_model: str,
) -> dict[str, Any]:
    # Embedding dispatch mutates the existing Chunk node by id. It does not
    # create a separate embedding node or rewrite the full chunk record.
    result = write_query(
        """
        MATCH (c:Chunk {id: $chunk_id})
        SET c.embedding = $embedding,
            c.embedding_status = "embedded",
            c.embedding_model = $embedding_model,
            c.last_embedding_job_id = $job_id,
            c.updated_at = localDateTime()
        RETURN c.id AS chunk_id
        """,
        {
            "job_id": job_id,
            "chunk_id": chunk_id,
            "embedding": embedding,
            "embedding_model": embedding_model,
        },
    )
    _require_updated_chunk(result, chunk_id)
    return result


def _require_updated_chunk(result: dict[str, Any], expected_chunk_id: str) -> None:
    rows = result.get("rows") or []
    updated_chunk_id = str(rows[0].get("chunk_id") or "") if rows else ""
    if updated_chunk_id != expected_chunk_id:
        raise ValueError(
            f"Chunk embedding update returned {updated_chunk_id or 'no chunk'}; "
            f"expected {expected_chunk_id}."
        )
