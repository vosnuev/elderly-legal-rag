from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline.services.embedding_dispatch_service import EmbeddingDispatchService


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_documents(self, texts):  # noqa: ANN001, ANN201
        self.calls.append(list(texts))
        text = texts[0]
        return [[float(len(text)), 1.0]]


class EmbeddingDispatchServiceTest(unittest.TestCase):
    def test_dispatch_embeds_and_updates_each_chunk_individually(self) -> None:
        embeddings = FakeEmbeddings()
        update_calls: list[dict[str, object]] = []

        def update_chunk_embedding(**kwargs):  # noqa: ANN003, ANN202
            update_calls.append(kwargs)
            return {"rows": [{"chunk_id": kwargs["chunk_id"]}]}

        with (
            patch(
                "pipeline.services.embedding_dispatch_service.create_openrouter_embeddings",
                return_value=embeddings,
            ),
            patch(
                "pipeline.services.embedding_dispatch_service.read_chunk_by_id",
                side_effect=lambda chunk_id: _chunk_record(chunk_id=chunk_id),
            ),
            patch(
                "pipeline.services.embedding_dispatch_service.update_chunk_embedding",
                side_effect=update_chunk_embedding,
            ),
        ):
            result = EmbeddingDispatchService().dispatch(
                job_id="job-1",
                chunk_ids=["chunk-1", "chunk-2"],
            )

        self.assertEqual(result, ["chunk-1", "chunk-2"])
        self.assertEqual(embeddings.calls, [["text for chunk-1"], ["text for chunk-2"]])
        self.assertEqual([call["chunk_id"] for call in update_calls], ["chunk-1", "chunk-2"])

    def test_dispatch_retries_missing_chunks_in_same_node(self) -> None:
        embeddings = FakeEmbeddings()
        update_attempts: dict[str, int] = {}

        def update_chunk_embedding(**kwargs):  # noqa: ANN003, ANN202
            chunk_id = str(kwargs["chunk_id"])
            update_attempts[chunk_id] = update_attempts.get(chunk_id, 0) + 1
            if chunk_id == "chunk-2" and update_attempts[chunk_id] == 1:
                raise RuntimeError("transient write failure")
            return {"rows": [{"chunk_id": chunk_id}]}

        with (
            patch(
                "pipeline.services.embedding_dispatch_service.create_openrouter_embeddings",
                return_value=embeddings,
            ),
            patch(
                "pipeline.services.embedding_dispatch_service.read_chunk_by_id",
                side_effect=lambda chunk_id: _chunk_record(chunk_id=chunk_id),
            ),
            patch(
                "pipeline.services.embedding_dispatch_service.update_chunk_embedding",
                side_effect=update_chunk_embedding,
            ),
        ):
            result = EmbeddingDispatchService().dispatch(
                job_id="job-1",
                chunk_ids=["chunk-1", "chunk-2"],
            )

        self.assertEqual(result, ["chunk-1", "chunk-2"])
        self.assertEqual(update_attempts, {"chunk-1": 1, "chunk-2": 2})
        self.assertEqual(
            embeddings.calls,
            [["text for chunk-1"], ["text for chunk-2"], ["text for chunk-2"]],
        )


def _chunk_record(*, chunk_id: str) -> dict[str, object]:
    return {
        "id": chunk_id,
        "document_id": "doc-1",
        "chunk_index": 0,
        "text": f"text for {chunk_id}",
        "start_unique_string": "start",
        "end_unique_string": "end",
    }


if __name__ == "__main__":
    unittest.main()
