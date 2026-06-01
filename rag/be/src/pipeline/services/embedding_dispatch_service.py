from __future__ import annotations

from datetime import UTC, datetime

from external.openrouter import create_openrouter_embeddings
from query.read.inspection import read_chunk_by_id
from query.schema import ChunkNode
from query.write import update_chunk_embeddings
from settings import settings


class EmbeddingDispatchService:
    def dispatch(self, *, job_id: str, chunk_ids: list[str]) -> list[str]:
        chunks = _load_chunks(chunk_ids)
        if not chunks:
            return []

        embeddings = create_openrouter_embeddings()
        updated_chunks: list[ChunkNode] = []

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
                        "embedding": vector,
                        "metadata": {
                            **chunk.metadata,
                            "embedding_created_at": created_at,
                        },
                    }
                )
            )

        update_chunk_embeddings(job_id=job_id, chunks=updated_chunks)
        return [chunk.id for chunk in updated_chunks]


def _load_chunks(chunk_ids: list[str]) -> list[ChunkNode]:
    return [
        ChunkNode.model_validate(read_chunk_by_id(chunk_id))
        for chunk_id in chunk_ids
    ]
