"""Observability event storage interfaces."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from observability.events.models import ObservabilityEvent


class ObservabilityPublisher(Protocol):
    async def publish(self, event: ObservabilityEvent) -> str | None:
        """Publish one event and return a backend event id when available."""


class ObservabilityReader(Protocol):
    async def read(
        self,
        *,
        job_id: str,
        last_event_id: str,
    ) -> AsyncIterator[ObservabilityEvent]:
        """Read job events after the given backend event id."""
