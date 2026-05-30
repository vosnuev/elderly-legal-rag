from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentToolContext:
    job_id: str
    agent_name: str
    operation_scope: str
    document_id: str | None = None
    chunk_id: str | None = None
    candidate_id: str | None = None

    def require_job_id(self) -> str:
        if not self.job_id.strip():
            raise ValueError("AgentToolContext.job_id is required.")
        return self.job_id

    def require_document_id(self) -> str:
        if not self.document_id or not self.document_id.strip():
            raise ValueError("AgentToolContext.document_id is required.")
        return self.document_id

    def require_candidate_id(self) -> str:
        if not self.candidate_id or not self.candidate_id.strip():
            raise ValueError("AgentToolContext.candidate_id is required.")
        return self.candidate_id


_current_context: ContextVar[AgentToolContext | None] = ContextVar(
    "agent_tool_context",
    default=None,
)
_current_raw_content: ContextVar[str | None] = ContextVar(
    "agent_tool_raw_content",
    default=None,
)


def get_current_agent_tool_context() -> AgentToolContext:
    context = _current_context.get()
    if context is None:
        raise RuntimeError("Agent tool context is not bound.")
    return context


def get_current_raw_content() -> str | None:
    return _current_raw_content.get()


@contextmanager
def bind_agent_tool_context(
    context: AgentToolContext,
    raw_content: str | None = None,
) -> Iterator[None]:
    context_token = _current_context.set(context)
    raw_content_token = _current_raw_content.set(raw_content)
    try:
        yield
    finally:
        _current_raw_content.reset(raw_content_token)
        _current_context.reset(context_token)
