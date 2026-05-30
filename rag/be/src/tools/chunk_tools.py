from __future__ import annotations

from typing import Any

from langchain.tools import tool

from query.service import get_memgraph_query_service
from tools.context import get_current_agent_tool_context, get_current_raw_content


@tool
def count_occurrences_tool(text: str) -> int:
    """Count exact occurrences of text in the bound source document raw content."""
    context = get_current_agent_tool_context()
    source = get_current_raw_content()
    if source is None:
        source = get_memgraph_query_service().get_document_raw_content(
            context.require_document_id()
        )
    return source.count(text)


@tool
def write_chunk_tool(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Write generated chunks for the bound document and ingest job."""
    context = get_current_agent_tool_context()
    document_id = context.require_document_id()
    job_id = context.require_job_id()
    records = []
    for chunk in chunks:
        record = dict(chunk)
        record.setdefault("document_id", document_id)
        records.append(record)
    return get_memgraph_query_service().store_chunks(
        job_id=job_id,
        document_id=document_id,
        chunks=records,
    )
