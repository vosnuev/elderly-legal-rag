"""In-memory task state and idempotency boundary."""

from __future__ import annotations

from threading import RLock
from uuid import uuid4

from knowledge_runtime.jobs.models import utc_now
from knowledge_runtime.tasks.models import (
    TaskKind,
    TaskRecord,
    TaskStatus,
    TaskSubmission,
)

_DEDUPED_STATUSES = {
    TaskStatus.QUEUED,
    TaskStatus.RUNNING,
    TaskStatus.SUCCEEDED,
}


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._idempotency: dict[str, str] = {}
        self._order: list[str] = []
        self._lock = RLock()

    def submit(
        self,
        *,
        kind: TaskKind,
        job_id: str,
        idempotency_key: str,
        payload: dict[str, object],
    ) -> TaskSubmission:
        with self._lock:
            existing_id = self._idempotency.get(idempotency_key)
            existing = self._tasks.get(existing_id or "")
            if existing and existing.status in _DEDUPED_STATUSES:
                return TaskSubmission(task=existing.model_copy(deep=True), accepted=False)

            task = TaskRecord(
                task_id=str(uuid4()),
                idempotency_key=idempotency_key,
                job_id=job_id,
                kind=kind,
                payload=dict(payload),
            )
            self._tasks[task.task_id] = task
            self._idempotency[idempotency_key] = task.task_id
            self._order.append(task.task_id)
            return TaskSubmission(task=task.model_copy(deep=True), accepted=True)

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.model_copy(deep=True) if task else None

    def current_for_job(self, job_id: str) -> TaskRecord | None:
        with self._lock:
            job_tasks = [
                self._tasks[task_id]
                for task_id in self._order
                if self._tasks[task_id].job_id == job_id
            ]
            active = [
                task
                for task in job_tasks
                if task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}
            ]
            selected = (active or job_tasks)[-1] if (active or job_tasks) else None
            return selected.model_copy(deep=True) if selected else None

    def mark_running(self, task_id: str) -> TaskRecord:
        with self._lock:
            task = self._require(task_id)
            task.status = TaskStatus.RUNNING
            task.started_at = utc_now()
            task.error = None
            return task.model_copy(deep=True)

    def mark_succeeded(self, task_id: str) -> TaskRecord:
        with self._lock:
            task = self._require(task_id)
            task.status = TaskStatus.SUCCEEDED
            task.finished_at = utc_now()
            task.error = None
            return task.model_copy(deep=True)

    def mark_failed(self, task_id: str, error: str) -> TaskRecord:
        with self._lock:
            task = self._require(task_id)
            task.status = TaskStatus.FAILED
            task.finished_at = utc_now()
            task.error = error
            return task.model_copy(deep=True)

    def _require(self, task_id: str) -> TaskRecord:
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task
