from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from knowledge_runtime.jobs.projector import JobProjector
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.schemas import DocumentWorkRequest, RegisteredDocument
from knowledge_runtime.service.documents import DocumentWorkService
from knowledge_runtime.tasks.store import TaskStore


class FakeRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def register_text(self, **kwargs):  # noqa: ANN003, ANN201
        self.calls.append(kwargs)
        return RegisteredDocument(
            document_id=f"doc-{kwargs['job_id']}",
            file_name=str(kwargs["file_name"]),
            content_type=str(kwargs["content_type"] or "text/plain"),
            content_hash="hash",
        )


class FakeSubmitter:
    def __init__(self) -> None:
        self.build_calls: list[tuple[str, str]] = []

    async def submit_build(self, *, job_id: str, document_id: str):  # noqa: ANN201
        self.build_calls.append((job_id, document_id))
        return SimpleNamespace(accepted=True)


class DocumentWorkServiceTest(unittest.TestCase):
    def test_create_text_registers_document_and_submits_build_task(self) -> None:
        registry = FakeRegistry()
        submitter = FakeSubmitter()
        job_store = JobStore()
        service = DocumentWorkService(
            registry=registry,
            job_store=job_store,
            submitter=submitter,
            projector=JobProjector(job_store=job_store, task_store=TaskStore()),
        )

        with patch(
            "knowledge_runtime.jobs.projector.summarize_job_progress",
            return_value={"rows": []},
        ):
            response = asyncio.run(
                service.create_text(
                    DocumentWorkRequest(file_name="sample.md", content="hello")
                )
            )

        self.assertEqual(response.current_phase.value, "stored")
        self.assertEqual(response.document_id, f"doc-{response.job_id}")
        self.assertEqual(submitter.build_calls, [(response.job_id, response.document_id)])
        self.assertEqual(registry.calls[0]["raw_content"], "hello")


if __name__ == "__main__":
    unittest.main()
