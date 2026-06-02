"""Submit build/review tasks to worker queues.

This module is the only place that knows task idempotency keys and queue
selection rules.
"""

from __future__ import annotations

from knowledge_runtime.tasks.models import TaskKind, TaskSubmission
from knowledge_runtime.tasks.store import TaskStore
from knowledge_runtime.workers.pool import WorkerPool
from observability.consume.service import ObservabilityService


class TaskSubmitter:
    def __init__(
        self,
        *,
        task_store: TaskStore,
        worker_pool: WorkerPool,
        observer: ObservabilityService,
    ) -> None:
        self._task_store = task_store
        self._worker_pool = worker_pool
        self._observer = observer

    async def submit_build(self, *, job_id: str, document_id: str) -> TaskSubmission:
        submission = self._task_store.submit(
            kind=TaskKind.BUILD,
            job_id=job_id,
            idempotency_key=f"build:{job_id}",
            payload={"job_id": job_id, "document_id": document_id},
        )
        if submission.accepted:
            await self._worker_pool.enqueue(submission.task)
            await self._observer.lifecycle(
                job_id=job_id,
                task_id=submission.task.task_id,
                kind=submission.task.kind.value,
                event="task.queued",
                stage="task_queue",
                edge="doc_to_queue",
                log="Build task queued.",
            )
            await self._worker_pool.publish_metrics(submission.task)
        return submission

    async def submit_review(
        self,
        *,
        job_id: str,
        candidate_id: str,
        action: str,
        reviewer: str,
        note: str | None,
    ) -> TaskSubmission:
        submission = self._task_store.submit(
            kind=TaskKind.REVIEW,
            job_id=job_id,
            idempotency_key=f"review:{job_id}:{candidate_id}",
            payload={
                "job_id": job_id,
                "candidate_id": candidate_id,
                "action": action,
                "reviewer": reviewer,
                "note": note,
            },
        )
        if submission.accepted:
            await self._worker_pool.enqueue(submission.task)
            await self._observer.lifecycle(
                job_id=job_id,
                task_id=submission.task.task_id,
                kind=submission.task.kind.value,
                event="task.queued",
                stage="task_queue",
                edge="candidate_to_queue",
                log="Review task queued.",
            )
            await self._worker_pool.publish_metrics(submission.task)
        return submission
