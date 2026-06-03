"""Build/review worker lane lifecycle boundary."""

from __future__ import annotations

import asyncio

from observability.logger import bind_logger
from knowledge_runtime.jobs.models import JobPhase
from knowledge_runtime.jobs.progress import JobProgressModifier
from knowledge_runtime.tasks.models import TaskKind, TaskRecord
from knowledge_runtime.tasks.store import TaskStore
from knowledge_runtime.workers.runner import PipelineRunner
from observability.consume.context import bind_observability_context
from observability.consume.service import ObservabilityService


class WorkerPool:
    def __init__(
        self,
        *,
        task_store: TaskStore,
        progress_modifier: JobProgressModifier,
        observer: ObservabilityService,
        runner: PipelineRunner,
        build_worker_count: int = 1,
        review_worker_count: int = 1,
        queue_max_size: int = 100,
    ) -> None:
        self._task_store = task_store
        self._progress_modifier = progress_modifier
        self._observer = observer
        self._runner = runner
        self._queues = {
            TaskKind.BUILD: asyncio.Queue[TaskRecord](maxsize=queue_max_size),
            TaskKind.REVIEW: asyncio.Queue[TaskRecord](maxsize=queue_max_size),
        }
        self._worker_counts = {
            TaskKind.BUILD: build_worker_count,
            TaskKind.REVIEW: review_worker_count,
        }
        self._active_counts = {
            TaskKind.BUILD: 0,
            TaskKind.REVIEW: 0,
        }
        self._workers: list[asyncio.Task[None]] = []
        self._logger = bind_logger(component="knowledge_worker_pool")

    async def start(self) -> None:
        if self._workers:
            return
        self._observer.bind_event_loop(asyncio.get_running_loop())
        for kind, count in self._worker_counts.items():
            for index in range(count):
                self._workers.append(
                    asyncio.create_task(
                        self._worker_loop(kind=kind, index=index),
                        name=f"knowledge-{kind.value}-worker-{index}",
                    )
                )
        self._logger.bind(
            build_worker_count=self._worker_counts[TaskKind.BUILD],
            review_worker_count=self._worker_counts[TaskKind.REVIEW],
        ).info("worker pool started")

    async def stop(self) -> None:
        workers = list(self._workers)
        self._workers.clear()
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        self._logger.info("worker pool stopped")

    async def enqueue(self, task: TaskRecord) -> None:
        await self._queues[task.kind].put(task)

    async def publish_metrics(self, task: TaskRecord) -> None:
        queue_count = self._queues[task.kind].qsize()
        active_tasks = self._active_counts[task.kind]
        worker_count = self._worker_counts[task.kind]
        worker_load = round((active_tasks / worker_count) * 100) if worker_count else 0
        await self._observer.worker_metrics(
            job_id=task.job_id,
            task_id=task.task_id,
            kind=task.kind.value,
            queue_count=queue_count,
            worker_load=worker_load,
            lane=task.kind.value,
            active_tasks=active_tasks,
        )

    async def _worker_loop(self, *, kind: TaskKind, index: int) -> None:
        queue = self._queues[kind]
        while True:
            task = await queue.get()
            try:
                await self._run_task(task)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self._logger.bind(
                    task_id=task.task_id,
                    job_id=task.job_id,
                    kind=kind.value,
                    worker_index=index,
                ).exception("worker task failed")
                await self._mark_failed(task, str(exc))
            finally:
                queue.task_done()

    async def _run_task(self, task: TaskRecord) -> None:
        running = self._task_store.mark_running(task.task_id)
        self._active_counts[running.kind] += 1
        with bind_observability_context(
            job_id=running.job_id,
            task_id=running.task_id,
            kind=running.kind.value,
        ):
            await self._observer.lifecycle(
                event="task.started",
                stage="task_queue",
                edge="queue_to_worker",
                log=f"{running.kind.value} task started.",
            )
            await self.publish_metrics(running)

            try:
                result = await self._runner.run(running)
                updated_job = self._progress_modifier.apply_task_result(
                    task=running,
                    result=result,
                )
                phase_source = (
                    updated_job.current_phase
                    if updated_job
                    else getattr(result, "phase", None)
                )
                phase = JobPhase.normalize(phase_source)
                await self._observer.lifecycle(
                    event="job.progress.persisted",
                    stage="job_progress",
                    edge=f"{running.kind.value}_result_to_job_state",
                    log=f"Job phase set to {phase.value}.",
                    data={
                        "phase": phase.value,
                        "document_id": updated_job.document_id if updated_job else None,
                        "chunk_count": updated_job.chunk_count if updated_job else 0,
                        "candidate_count": (
                            updated_job.candidate_count if updated_job else 0
                        ),
                        "pending_review_count": (
                            updated_job.pending_review_count if updated_job else 0
                        ),
                    },
                )
                errors = [str(error) for error in getattr(result, "errors", []) or []]
                if phase is JobPhase.FAILED:
                    await self._mark_failed(
                        running,
                        errors[0] if errors else "Task failed.",
                        update_job=False,
                    )
                    return

                succeeded = self._task_store.mark_succeeded(running.task_id)
                await self._observer.lifecycle(
                    job_id=succeeded.job_id,
                    task_id=succeeded.task_id,
                    kind=succeeded.kind.value,
                    event="task.succeeded",
                    stage="completed",
                    log=f"{succeeded.kind.value} task succeeded.",
                    data={"phase": phase.value},
                )
            finally:
                self._active_counts[running.kind] = max(
                    self._active_counts[running.kind] - 1,
                    0,
                )
                await self.publish_metrics(running)

    async def _mark_failed(
        self,
        task: TaskRecord,
        error: str,
        *,
        update_job: bool = True,
    ) -> None:
        failed = self._task_store.mark_failed(task.task_id, error)
        if update_job:
            self._progress_modifier.mark_task_failed(task=failed, error=error)
        await self._observer.lifecycle(
            job_id=failed.job_id,
            task_id=failed.task_id,
            kind=failed.kind.value,
            event="task.failed",
            stage="completed",
            log=error,
            data={"phase": JobPhase.FAILED.value, "error": error},
        )
