"""Context binding for runtime code that emits job observability events."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from collections.abc import Iterator


@dataclass(frozen=True)
class ObservabilityContext:
    job_id: str | None = None
    task_id: str | None = None
    kind: str | None = None


_context: ContextVar[ObservabilityContext] = ContextVar(
    "observability_context",
    default=ObservabilityContext(),
)


def get_observability_context() -> ObservabilityContext:
    return _context.get()


@contextmanager
def bind_observability_context(
    *,
    job_id: str | None = None,
    task_id: str | None = None,
    kind: str | None = None,
) -> Iterator[ObservabilityContext]:
    current = _context.get()
    bound = ObservabilityContext(
        job_id=job_id or current.job_id,
        task_id=task_id or current.task_id,
        kind=kind or current.kind,
    )
    token = _context.set(bound)
    try:
        yield bound
    finally:
        _context.reset(token)
