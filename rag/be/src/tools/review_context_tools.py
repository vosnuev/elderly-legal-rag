from __future__ import annotations

from langchain.tools import tool

from query.service import get_memgraph_query_service
from tools.context import get_current_agent_tool_context


@tool
def get_reviewer_notes_tool(context_text: str, limit: int = 10) -> dict[str, object]:
    """Read reviewer notes related to current candidate generation context."""
    return get_memgraph_query_service().find_review_notes(context_text, limit)


@tool
def get_ingest_state_tool() -> dict[str, object]:
    """Read persisted ingest progress for the bound ingest job."""
    context = get_current_agent_tool_context()
    return get_memgraph_query_service().get_ingest_progress(context.require_job_id())
