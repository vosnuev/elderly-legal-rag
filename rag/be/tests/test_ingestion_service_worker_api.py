from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from api.ingest.jobs import list_ingest_jobs, stream_ingest_job_events
from knowledge_runtime.documents.registry import DocumentRegistry
from knowledge_runtime.jobs.projector import JobProjector
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.jobs.models import JobPhase
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
    def test_document_registry_accepts_toon_documents(self) -> None:
        registry = DocumentRegistry()

        with patch(
            "knowledge_runtime.documents.registry.register_document",
            return_value={"rows": [{"document_id": "doc-toon"}]},
        ):
            document = registry.register_text(
                job_id="job-toon",
                file_name="sample.toon",
                raw_content="title: sample\nbody: toon content",
            )

        self.assertEqual(document.document_id, "doc-toon")
        self.assertEqual(document.content_type, "toon")

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

        with (
            patch(
                "knowledge_runtime.jobs.projector.summarize_job_progress",
                return_value={"rows": []},
            ),
            patch(
                "knowledge_runtime.service.documents.upsert_ingest_job_progress",
                return_value={"rows": []},
            ) as upsert_job,
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
        upsert_job.assert_called_once()

    def test_projector_lists_persisted_jobs_after_process_memory_is_empty(self) -> None:
        projector = JobProjector(job_store=JobStore(), task_store=TaskStore())

        with patch(
            "knowledge_runtime.jobs.projector.list_ingest_job_progress",
            return_value={
                "rows": [
                    {
                        "job": {
                            "properties": {
                                "id": "job-1",
                                "job_id": "job-1",
                                "phase": "pending_review",
                                "document_id": "doc-1",
                                "chunk_count": 2,
                                "candidate_count": 3,
                                "pending_review_count": 1,
                            }
                        },
                        "document": {"properties": {"id": "doc-1", "file_name": "sample.md"}},
                        "candidate_count": 3,
                        "pending_review_count": 1,
                    }
                ]
            },
        ):
            response = projector.list(limit=10)

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].job_id, "job-1")
        self.assertEqual(response[0].file_name, "sample.md")
        self.assertEqual(response[0].current_phase, JobPhase.PENDING_REVIEW)
        self.assertEqual(response[0].document_id, "doc-1")
        self.assertEqual(response[0].chunk_count, 2)
        self.assertEqual(response[0].candidate_count, 3)
        self.assertEqual(response[0].pending_review_count, 1)
        self.assertIsNone(response[0].current_task)

    def test_projector_status_reads_persisted_job_when_runtime_store_is_empty(self) -> None:
        projector = JobProjector(job_store=JobStore(), task_store=TaskStore())

        with patch(
            "knowledge_runtime.jobs.projector.summarize_job_progress",
            return_value={
                "rows": [
                    {
                        "job": {
                            "properties": {
                                "id": "job-1",
                                "job_id": "job-1",
                                "phase": "completed",
                                "document_id": "doc-1",
                            }
                        },
                        "document": {"properties": {"id": "doc-1", "file_name": "sample.md"}},
                        "candidate_count": 3,
                        "pending_review_count": 0,
                    }
                ]
            },
        ):
            response = projector.status("job-1")

        self.assertEqual(response.job_id, "job-1")
        self.assertEqual(response.file_name, "sample.md")
        self.assertEqual(response.current_phase, JobPhase.COMPLETED)
        self.assertEqual(response.document_id, "doc-1")
        self.assertTrue(response.completed)

    def test_job_list_route_delegates_to_runtime_status_service(self) -> None:
        with patch("api.ingest.jobs.knowledge_runtime") as runtime:
            runtime.status.list.return_value = []

            response = list_ingest_jobs(limit=7)

        self.assertEqual(response, [])
        runtime.status.list.assert_called_once_with(limit=7)

    def test_job_event_route_delegates_to_runtime_status_service(self) -> None:
        with patch("api.ingest.jobs.knowledge_runtime") as runtime:
            runtime.status.events.return_value = object()

            response = stream_ingest_job_events("job-1", last_event_id="1-0")

        self.assertEqual(response, runtime.status.events.return_value)
        runtime.status.events.assert_called_once_with("job-1", last_event_id="1-0")


if __name__ == "__main__":
    unittest.main()
