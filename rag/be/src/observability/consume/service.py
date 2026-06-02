"""Runtime-facing observability service consumed by workers and pipeline code."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from observability.logger import bind_logger
from observability.consume.context import get_observability_context
from observability.events.models import (
    ObservabilityChannel,
    ObservabilityEvent,
    VisibilityEventType,
)
from observability.events.ports import ObservabilityPublisher, ObservabilityReader
from observability.redis import RedisStreamObservability
from settings import settings


class ObservabilityService:
    def __init__(
        self,
        *,
        publisher: ObservabilityPublisher,
        reader: ObservabilityReader,
    ) -> None:
        self._publisher = publisher
        self._reader = reader
        self._logger = bind_logger(component="observability")
        self._event_loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    def create_default(cls) -> "ObservabilityService":
        redis_observer = RedisStreamObservability.from_settings()
        return cls(publisher=redis_observer, reader=redis_observer)

    async def publish(self, event: ObservabilityEvent) -> str | None:
        if not settings.observability_enabled:
            return None
        self.bind_event_loop()
        try:
            event_id = await self._publisher.publish(event)
            self._logger.bind(
                job_id=event.job_id,
                task_id=event.task_id,
                channel=str(event.channel),
                event_id=event_id,
            ).debug("observability event published")
            return event_id
        except Exception as exc:  # noqa: BLE001
            self._logger.bind(
                job_id=event.job_id,
                task_id=event.task_id,
                channel=str(event.channel),
                error=str(exc),
            ).warning("observability publish failed")
            return None

    def bind_event_loop(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._event_loop = loop or asyncio.get_running_loop()

    def publish_from_thread(self, event: ObservabilityEvent) -> str | None:
        """Publish from sync graph/agent code running inside worker threads."""
        if not settings.observability_enabled:
            return None
        loop = self._event_loop
        if loop is None or not loop.is_running():
            return None

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is loop:
            loop.create_task(self.publish(event))
            return None

        future = asyncio.run_coroutine_threadsafe(self.publish(event), loop)
        try:
            return future.result(timeout=2)
        except Exception as exc:  # noqa: BLE001
            self._logger.bind(
                job_id=event.job_id,
                task_id=event.task_id,
                channel=str(event.channel),
                error=str(exc),
            ).warning("observability thread publish failed")
            return None

    async def lifecycle(
        self,
        *,
        job_id: str | None = None,
        task_id: str | None = None,
        kind: str | None = None,
        event: str,
        log: str,
        stage: str | None = None,
        edge: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> str | None:
        context = get_observability_context()
        resolved_job_id = job_id or context.job_id
        if not resolved_job_id:
            return None
        return await self.publish(
            ObservabilityEvent(
                job_id=resolved_job_id,
                task_id=task_id or context.task_id,
                kind=kind or context.kind,
                channel=ObservabilityChannel.AGENT_TRANSCRIPT,
                payload={
                    "type": VisibilityEventType.LIFECYCLE.value,
                    "event": event,
                    "stage": stage,
                    "edge": edge,
                    "log": log,
                    **(data or {}),
                },
            )
        )

    async def service(
        self,
        *,
        job_id: str | None = None,
        task_id: str | None = None,
        kind: str | None = None,
        service_name: str,
        log: str,
        stage: str | None = None,
        edge: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> str | None:
        context = get_observability_context()
        resolved_job_id = job_id or context.job_id
        if not resolved_job_id:
            return None
        return await self.publish(
            ObservabilityEvent(
                job_id=resolved_job_id,
                task_id=task_id or context.task_id,
                kind=kind or context.kind,
                channel=ObservabilityChannel.AGENT_TRANSCRIPT,
                payload={
                    "type": VisibilityEventType.SERVICE.value,
                    "stage": stage,
                    "edge": edge,
                    "log": log,
                    "serviceName": service_name,
                    **(data or {}),
                },
            )
        )

    async def agent(
        self,
        *,
        job_id: str | None = None,
        task_id: str | None = None,
        kind: str | None = None,
        agent_name: str,
        log: str,
        stage: str | None = None,
        edge: str | None = None,
        token: str | None = None,
        diagnostic_note: str | None = None,
        tool_usage: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> str | None:
        context = get_observability_context()
        resolved_job_id = job_id or context.job_id
        if not resolved_job_id:
            return None
        payload: dict[str, Any] = {
            "type": VisibilityEventType.AGENT.value,
            "stage": stage,
            "edge": edge,
            "log": log,
            "agentName": agent_name,
            **(data or {}),
        }
        if token is not None:
            payload["token"] = token
        if diagnostic_note is not None:
            payload["diagnosticNote"] = diagnostic_note
            payload["thought"] = diagnostic_note
        if tool_usage is not None:
            payload["toolUsage"] = tool_usage
        return await self.publish(
            ObservabilityEvent(
                job_id=resolved_job_id,
                task_id=task_id or context.task_id,
                kind=kind or context.kind,
                channel=ObservabilityChannel.AGENT_TRANSCRIPT,
                payload=payload,
            )
        )

    def agent_from_thread(
        self,
        *,
        job_id: str | None = None,
        task_id: str | None = None,
        kind: str | None = None,
        agent_name: str,
        log: str,
        stage: str | None = None,
        edge: str | None = None,
        token: str | None = None,
        diagnostic_note: str | None = None,
        tool_usage: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> str | None:
        context = get_observability_context()
        resolved_job_id = job_id or context.job_id
        if not resolved_job_id:
            return None
        payload: dict[str, Any] = {
            "type": VisibilityEventType.AGENT.value,
            "stage": stage,
            "edge": edge,
            "log": log,
            "agentName": agent_name,
            **(data or {}),
        }
        if token is not None:
            payload["token"] = token
        if diagnostic_note is not None:
            payload["diagnosticNote"] = diagnostic_note
            payload["thought"] = diagnostic_note
        if tool_usage is not None:
            payload["toolUsage"] = tool_usage
        return self.publish_from_thread(
            ObservabilityEvent(
                job_id=resolved_job_id,
                task_id=task_id or context.task_id,
                kind=kind or context.kind,
                channel=ObservabilityChannel.AGENT_TRANSCRIPT,
                payload=payload,
            )
        )

    async def worker_metrics(
        self,
        *,
        job_id: str,
        task_id: str | None = None,
        kind: str | None = None,
        queue_count: int,
        worker_load: int,
        lane: str,
        active_tasks: int,
    ) -> str | None:
        return await self.publish(
            ObservabilityEvent(
                job_id=job_id,
                task_id=task_id,
                kind=kind,
                channel=ObservabilityChannel.WORKER_METRICS,
                payload={
                    "queue_count": queue_count,
                    "worker_load": worker_load,
                    "lane": lane,
                    "active_tasks": active_tasks,
                },
            )
        )

    async def read(
        self,
        *,
        job_id: str,
        last_event_id: str = "0-0",
    ) -> AsyncIterator[ObservabilityEvent]:
        async for event in self._reader.read(
            job_id=job_id,
            last_event_id=last_event_id,
        ):
            yield event


observer = ObservabilityService.create_default()
