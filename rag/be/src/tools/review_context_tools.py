from __future__ import annotations

from langchain.tools import tool

from query.read.discovery import text_search
from settings import settings
from tools.agent_output_sanitize import sanitize_agent_tool_output


@tool
def get_reviewer_notes_tool(context_text: str, limit: int = 10) -> dict[str, object]:
    """Read reviewer notes related to current candidate generation context."""
    return sanitize_agent_tool_output(
        text_search(
            context_text,
            top_k=limit,
            index_name=settings.review_note_text_search_index_name,
        )
    )
