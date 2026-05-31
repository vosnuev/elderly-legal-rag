from __future__ import annotations

from typing import Any

from langchain.tools import tool

from query.read import get_document_raw_content
from query.utils import graph_properties
from query.write import write_query
from tools.context import get_current_agent_tool_context, get_current_raw_content


@tool
def count_occurrences_tool(text: str) -> int:
    """Count exact occurrences of text in the bound source document raw content."""
    context = get_current_agent_tool_context()
    source = get_current_raw_content()
    if source is None:
        source = get_document_raw_content(context.require_document_id())
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
    return write_query(
        """
        MATCH (d:Document {id: $document_id})
        UNWIND $chunks AS chunk
        MERGE (c:Chunk {id: chunk.id})
        SET c += chunk,
            c.document_id = $document_id,
            c.last_ingest_job_id = $job_id
        MERGE (d)-[:HAS_CHUNK]->(c)
        RETURN count(c) AS stored_count
        """,
        {
            "job_id": job_id,
            "document_id": document_id,
            "chunks": [graph_properties(record) for record in records],
        },
    )
