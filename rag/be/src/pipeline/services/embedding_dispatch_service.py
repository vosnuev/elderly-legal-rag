from __future__ import annotations

from collections.abc import Sequence

from external.openrouter import create_openrouter_embeddings
from query.read.inspection import read_chunk_by_id
from query.schema import ChunkNode
from query.write import update_chunk_embedding
from settings import settings


class EmbeddingDispatchService:
    def dispatch(self, *, job_id: str, chunk_ids: list[str]) -> list[str]:
        if not chunk_ids:
            return []

        embeddings = create_openrouter_embeddings()
        if embeddings is None:
            raise RuntimeError(
                "embedding_dispatch_service requires RAG_OPENROUTER_API_KEY."
            )

        # Embed each chunk independently so the pipeline can retry only the
        # chunks that failed inside this same graph node.
        embedded_chunk_ids = _embed_chunk_ids(
            embeddings=embeddings,
            job_id=job_id,
            chunk_ids=chunk_ids,
        )
        missing_chunk_ids = _missing_chunk_ids(
            expected_chunk_ids=chunk_ids,
            embedded_chunk_ids=embedded_chunk_ids,
        )
        if missing_chunk_ids:
            # Same-node retry: do not advance to candidate generation until
            # every upstream chunk_id has an embedding stored on its Chunk node.
            embedded_chunk_ids.extend(
                _embed_chunk_ids(
                    embeddings=embeddings,
                    job_id=job_id,
                    chunk_ids=missing_chunk_ids,
                )
            )

        missing_chunk_ids = _missing_chunk_ids(
            expected_chunk_ids=chunk_ids,
            embedded_chunk_ids=embedded_chunk_ids,
        )
        if missing_chunk_ids:
            raise ValueError(
                "Embedding failed for chunks: "
                f"{', '.join(missing_chunk_ids)}"
            )

        # Preserve upstream chunk order in shared graph state after all updates
        # are confirmed. Retry order should not leak into downstream agents.
        return chunk_ids


def _embed_chunk_ids(
    *,
    embeddings: object,
    job_id: str,
    chunk_ids: list[str],
) -> list[str]:
    embedded_chunk_ids: list[str] = []
    for chunk_id in chunk_ids:
        try:
            embedded_chunk_ids.append(
                _embed_one_chunk(
                    embeddings=embeddings,
                    job_id=job_id,
                    chunk_id=chunk_id,
                )
            )
        except Exception:  # noqa: BLE001
            continue
    return embedded_chunk_ids


def _embed_one_chunk(
    *,
    embeddings: object,
    job_id: str,
    chunk_id: str,
) -> str:
    chunk = ChunkNode.model_validate(read_chunk_by_id(chunk_id))
    if not chunk.id:
        raise ValueError("Chunk id is required for embedding update.")

    # This updates the existing Chunk node only; embedding dispatch never creates
    # a new graph node or replaces the chunk payload.
    vector = embeddings.embed_documents([chunk.text])[0]
    update_chunk_embedding(
        job_id=job_id,
        chunk_id=chunk.id,
        embedding=vector,
        embedding_model=settings.embedding_model,
    )
    return chunk.id


def _missing_chunk_ids(
    *,
    expected_chunk_ids: Sequence[str],
    embedded_chunk_ids: Sequence[str],
) -> list[str]:
    embedded = set(embedded_chunk_ids)
    return [
        chunk_id
        for chunk_id in expected_chunk_ids
        if chunk_id not in embedded
    ]
