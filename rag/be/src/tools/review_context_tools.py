from __future__ import annotations

from langchain.tools import tool

from query.read import read_query, text_search
from settings import settings
from tools.context import get_current_agent_tool_context


@tool
def get_reviewer_notes_tool(context_text: str, limit: int = 10) -> dict[str, object]:
    """Read reviewer notes related to current candidate generation context."""
    return text_search(
        context_text,
        top_k=limit,
        index_name=settings.review_note_text_search_index_name,
    )


@tool
def get_ingest_state_tool() -> dict[str, object]:
    """Read persisted ingest progress for the bound ingest job."""
    context = get_current_agent_tool_context()
    return read_query(
        """
        MATCH (job:IngestJob {id: $job_id})
        RETURN job
        LIMIT 1
        """,
        {"job_id": context.require_job_id()},
    )
