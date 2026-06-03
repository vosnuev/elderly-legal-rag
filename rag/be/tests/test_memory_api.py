from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from api.operations.memory import get_global_memory, update_global_memory
from knowledge_runtime.schemas import MemoryDocumentUpdateRequest
from knowledge_runtime.service.memory import MemoryService


class MemoryApiTest(unittest.TestCase):
    def test_memory_route_reads_global_memory(self) -> None:
        with patch("api.operations.memory.knowledge_runtime") as runtime:
            runtime.memory.get_global.return_value = SimpleNamespace(version=3)

            response = get_global_memory()

        self.assertEqual(response.version, 3)
        runtime.memory.get_global.assert_called_once_with()

    def test_memory_route_updates_global_memory(self) -> None:
        request = MemoryDocumentUpdateRequest(content="memory", title="title")
        with patch("api.operations.memory.knowledge_runtime") as runtime:
            runtime.memory.update_global.return_value = SimpleNamespace(version=4)

            response = update_global_memory(request)

        self.assertEqual(response.version, 4)
        runtime.memory.update_global.assert_called_once_with(request)

    def test_memory_service_returns_empty_default_when_no_memory_exists(self) -> None:
        service = MemoryService()

        with patch(
            "knowledge_runtime.service.memory.list_memory",
            return_value={"rows": []},
        ):
            response = service.get_global()

        self.assertFalse(response.exists)
        self.assertEqual(response.scope, "global")
        self.assertEqual(response.version, 0)
        self.assertEqual(response.content, "")

    def test_memory_service_updates_memory_document(self) -> None:
        service = MemoryService()

        with (
            patch("knowledge_runtime.service.memory.update_memory_document") as update_memory,
            patch(
                "knowledge_runtime.service.memory.list_memory",
                return_value={
                    "rows": [
                        {
                            "memory": {
                                "properties": {
                                    "id": "memory-1",
                                    "scope": "global",
                                    "title": "Manual memory",
                                    "content": "updated",
                                    "version": 2,
                                    "status": "active",
                                    "author": "tester",
                                    "evidence_review_note_ids": ["note-1"],
                                    "evidence_relationship_candidate_ids": ["candidate-1"],
                                }
                            }
                        }
                    ]
                },
            ),
        ):
            response = service.update_global(
                MemoryDocumentUpdateRequest(
                    content="updated",
                    title="Manual memory",
                    update_summary="manual",
                    author="tester",
                )
            )

        update_memory.assert_called_once_with(
            content="updated",
            scope="global",
            title="Manual memory",
            update_summary="manual",
            author="tester",
        )
        self.assertTrue(response.exists)
        self.assertEqual(response.id, "memory-1")
        self.assertEqual(response.version, 2)
        self.assertEqual(response.evidence_review_note_ids, ["note-1"])
        self.assertEqual(response.evidence_candidate_ids, ["candidate-1"])


if __name__ == "__main__":
    unittest.main()
