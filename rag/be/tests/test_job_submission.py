from __future__ import annotations

import unittest
from unittest.mock import patch

from knowledge_runtime.jobs.models import JobPhase, JobStage, JobStageStatus
from knowledge_runtime.jobs.progress import JobProgressModifier
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.tasks.models import TaskKind, TaskRecord
from pipeline.schemas import GraphIngestPhase, IngestGraphResult


class JobProgressModifierTest(unittest.TestCase):
    def test_build_result_becomes_pending_review_when_candidates_wait(self) -> None:
        store = _store_with_job()
        modifier = JobProgressModifier(job_store=store)
        persisted: list[dict[str, object]] = []

        with (
            patch(
                "knowledge_runtime.jobs.progress.summarize_candidate_review_progress",
                return_value={"rows": [{"candidate_count": 2, "pending_review_count": 2}]},
            ),
            patch(
                "knowledge_runtime.jobs.progress.upsert_ingest_job_progress",
                side_effect=lambda **kwargs: persisted.append(kwargs),
            ),
        ):
            updated = modifier.apply_task_result(
                task=_task(kind=TaskKind.BUILD),
                result=IngestGraphResult(
                    job_id="job-1",
                    phase=GraphIngestPhase.COMPLETED,
                    document_id="doc-1",
                    chunk_count=3,
                ),
            )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.current_phase, JobPhase.PENDING_REVIEW)
        self.assertEqual(updated.candidate_count, 2)
        self.assertEqual(updated.pending_review_count, 2)
        self.assertEqual(persisted[0]["phase"], "pending_review")

    def test_review_result_completes_job_when_no_candidates_wait(self) -> None:
        store = _store_with_job(
            current_phase=JobPhase.PENDING_REVIEW,
            chunk_count=3,
            candidate_count=2,
            pending_review_count=1,
        )
        modifier = JobProgressModifier(job_store=store)
        persisted: list[dict[str, object]] = []

        with (
            patch(
                "knowledge_runtime.jobs.progress.summarize_candidate_review_progress",
                return_value={"rows": [{"candidate_count": 2, "pending_review_count": 0}]},
            ),
            patch(
                "knowledge_runtime.jobs.progress.upsert_ingest_job_progress",
                side_effect=lambda **kwargs: persisted.append(kwargs),
            ),
        ):
            updated = modifier.apply_task_result(
                task=_task(kind=TaskKind.REVIEW),
                result=IngestGraphResult(
                    job_id="job-1",
                    phase=GraphIngestPhase.COMPLETED,
                ),
            )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.current_phase, JobPhase.COMPLETED)
        self.assertTrue(updated.completed)
        self.assertEqual(updated.chunk_count, 3)
        self.assertEqual(updated.candidate_count, 2)
        self.assertEqual(updated.pending_review_count, 0)
        self.assertEqual(persisted[0]["phase"], "completed")

    def test_task_failure_is_persisted_as_failed_job_progress(self) -> None:
        store = _store_with_job(current_phase=JobPhase.PENDING_REVIEW)
        modifier = JobProgressModifier(job_store=store)
        persisted: list[dict[str, object]] = []

        with patch(
            "knowledge_runtime.jobs.progress.upsert_ingest_job_progress",
            side_effect=lambda **kwargs: persisted.append(kwargs),
        ):
            updated = modifier.mark_task_failed(
                task=_task(kind=TaskKind.BUILD),
                error="construction failed",
            )

        self.assertEqual(updated.current_phase, JobPhase.FAILED)
        self.assertEqual(updated.stages[-1].error, "construction failed")
        self.assertEqual(persisted[0]["phase"], "failed")
        self.assertEqual(persisted[0]["errors"], ["construction failed"])


def _store_with_job(
    *,
    current_phase: JobPhase = JobPhase.STORED,
    chunk_count: int = 0,
    candidate_count: int = 0,
    pending_review_count: int = 0,
) -> JobStore:
    store = JobStore()
    store.save(
        store_record(
            current_phase=current_phase,
            chunk_count=chunk_count,
            candidate_count=candidate_count,
            pending_review_count=pending_review_count,
        )
    )
    return store


def store_record(
    *,
    current_phase: JobPhase,
    chunk_count: int,
    candidate_count: int,
    pending_review_count: int,
):
    from knowledge_runtime.jobs.models import JobRecord

    return JobRecord(
        job_id="job-1",
        file_name="sample.md",
        current_phase=current_phase,
        document_id="doc-1",
        chunk_count=chunk_count,
        candidate_count=candidate_count,
        pending_review_count=pending_review_count,
        stages=[
            JobStage(
                phase=JobPhase.STORED,
                status=JobStageStatus.SUCCESS,
                message="Stored original document.",
            )
        ],
    )


def _task(*, kind: TaskKind) -> TaskRecord:
    return TaskRecord(
        task_id=f"{kind.value}-task-1",
        idempotency_key=f"{kind.value}:job-1",
        job_id="job-1",
        kind=kind,
        payload={},
    )


if __name__ == "__main__":
    unittest.main()
