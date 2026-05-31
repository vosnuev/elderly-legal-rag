from __future__ import annotations

from datetime import UTC, datetime

from external.openrouter import create_openrouter_embeddings
from pipeline.schemas import GraphChunk
from query.utils import graph_properties
from query.write import write_query
from settings import settings


class EmbeddingDispatchService:
    def dispatch(self, *, job_id: str, chunks: list[GraphChunk]) -> list[GraphChunk]:
        embeddings = create_openrouter_embeddings()
        updated_chunks: list[GraphChunk] = []

        if embeddings is None:
            raise RuntimeError(
                "embedding_dispatch_service requires RAG_OPENROUTER_API_KEY."
            )

        vectors = embeddings.embed_documents([chunk.text for chunk in chunks])
        created_at = datetime.now(UTC).isoformat()
        for chunk, vector in zip(chunks, vectors, strict=True):
            updated_chunks.append(
                chunk.model_copy(
                    update={
                        "embedding_status": "embedded",
                        "embedding_model": settings.embedding_model,
                        "embedding_dimensions": settings.embedding_dimensions,
                        "embedding": vector,
                        "metadata": {
                            **chunk.metadata,
                            "embedding_created_at": created_at,
                        },
                    }
                )
            )

        write_query(
            """
            UNWIND $chunks AS chunk
            MATCH (c:Chunk {id: chunk.id})
            SET c.embedding_status = chunk.embedding_status,
                c.embedding_model = chunk.embedding_model,
                c.embedding_dimensions = chunk.embedding_dimensions,
                c.embedding = chunk.embedding,
                c.last_embedding_job_id = $job_id
            RETURN count(c) AS stored_count
            """,
            {
                "job_id": job_id,
                "chunks": [
                    graph_properties(chunk.model_dump())
                    for chunk in updated_chunks
                ],
            },
        )
        return updated_chunks
