from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.utils import graph_properties


class ChunkRepository:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def store_chunks(
        self,
        job_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not chunks:
            return {"stored_count": 0}
        query = """
        MATCH (d:Document {id: $document_id})
        UNWIND $chunks AS chunk
        MERGE (c:Chunk {id: chunk.id})
        SET c += chunk,
            c.document_id = $document_id,
            c.last_ingest_job_id = $job_id
        MERGE (d)-[:HAS_CHUNK]->(c)
        RETURN count(c) AS stored_count
        """
        return self._client.execute_write(
            query,
            {
                "job_id": job_id,
                "document_id": document_id,
                "chunks": [graph_properties(chunk) for chunk in chunks],
            },
        )

    def store_chunk_embeddings(
        self,
        job_id: str,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not chunks:
            return {"stored_count": 0}
        query = """
        UNWIND $chunks AS chunk
        MATCH (c:Chunk {id: chunk.id})
        SET c.embedding_status = chunk.embedding_status,
            c.embedding_model = chunk.embedding_model,
            c.embedding_dimensions = chunk.embedding_dimensions,
            c.embedding = chunk.embedding,
            c.last_embedding_job_id = $job_id
        RETURN count(c) AS stored_count
        """
        return self._client.execute_write(
            query,
            {
                "job_id": job_id,
                "chunks": [graph_properties(chunk) for chunk in chunks],
            },
        )
