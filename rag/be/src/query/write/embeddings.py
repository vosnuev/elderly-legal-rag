from __future__ import annotations

from typing import Any

from query.schema import ChunkNode
from query.utils import graph_properties
from query.write.core import write_query


def update_chunk_embeddings(
    *,
    job_id: str,
    chunks: list[ChunkNode],
) -> dict[str, Any]:
    if not chunks:
        return {"stored_count": 0}
    return write_query(
        """
        UNWIND $chunks AS chunk
        MATCH (c:Chunk {id: chunk.id})
        SET c.embedding_status = chunk.embedding_status,
            c.embedding_model = chunk.embedding_model,
            c.embedding = chunk.embedding,
            c.last_embedding_job_id = $job_id
        RETURN count(c) AS stored_count
        """,
        {
            "job_id": job_id,
            "chunks": [
                graph_properties(chunk.model_dump())
                for chunk in chunks
            ],
        },
    )
