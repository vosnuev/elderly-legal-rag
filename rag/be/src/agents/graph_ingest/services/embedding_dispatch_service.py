from __future__ import annotations

from datetime import UTC, datetime

from agents.graph_ingest.schemas import GraphChunk
from agents.llm_clients.factory import create_openrouter_embeddings
from query.service import MemgraphQueryService, get_memgraph_query_service
from settings import settings


class EmbeddingDispatchService:
    def __init__(self, query_service: MemgraphQueryService | None = None) -> None:
        self._query_service = query_service or get_memgraph_query_service()

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

        self._query_service.store_chunk_embeddings(
            job_id,
            [chunk.model_dump() for chunk in updated_chunks],
        )
        return updated_chunks
