"""Adapter from worker tasks to pipeline invocation.

Pipeline code should be called from here, not from API routes or task stores.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pipeline.schemas import IngestGraphResult, ReviewAction

from knowledge_runtime.tasks.models import TaskKind, TaskRecord


class PipelineRunner:
    def __init__(self, invocation: object | None = None) -> None:
        self._invocation = invocation

    async def run(self, task: TaskRecord) -> IngestGraphResult:
        if task.kind is TaskKind.BUILD:
            return await self._run_build(task.payload)
        if task.kind is TaskKind.REVIEW:
            return await self._run_review(task.payload)
        raise ValueError(f"Unsupported task kind: {task.kind}")

    async def _run_build(self, payload: dict[str, Any]) -> IngestGraphResult:
        invocation = self._get_invocation()
        return await asyncio.to_thread(
            invocation.start_construction,
            job_id=str(payload["job_id"]),
            document_id=str(payload["document_id"]),
        )

    async def _run_review(self, payload: dict[str, Any]) -> IngestGraphResult:
        invocation = self._get_invocation()
        if "decisions" in payload:
            decisions = [
                {
                    "candidate_id": str(decision["candidate_id"]),
                    "action": ReviewAction(str(decision["action"])),
                    "note": decision.get("note"),
                }
                for decision in payload.get("decisions", [])
            ]
            result = await asyncio.to_thread(
                invocation.apply_review_decisions,
                job_id=str(payload["job_id"]),
                reviewer=str(payload["reviewer"]),
                decisions=decisions,
            )
        else:
            result = await asyncio.to_thread(
                invocation.apply_review_decision,
                candidate_id=str(payload["candidate_id"]),
                action=ReviewAction(str(payload["action"])),
                reviewer=str(payload["reviewer"]),
                note=payload.get("note"),
            )
        if result.job_id:
            return result
        return result.model_copy(update={"job_id": str(payload["job_id"])})

    def _get_invocation(self) -> object:
        if self._invocation is None:
            from pipeline.invocation import GraphIngestInvocation as PipelineInvocation

            self._invocation = PipelineInvocation()
        return self._invocation
