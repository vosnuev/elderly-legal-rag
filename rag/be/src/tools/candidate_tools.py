from __future__ import annotations

from typing import Any

from langchain.tools import tool

from query.service import get_memgraph_query_service
from tools.context import AgentToolContext, get_current_agent_tool_context


@tool
def write_relationship_candidate_tool(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write relationship candidates for pending human review."""
    context = get_current_agent_tool_context()
    return get_memgraph_query_service().store_edge_candidates(
        context.require_job_id(),
        [_candidate_record(context, candidate) for candidate in candidates],
    )


@tool
def write_candidate_revision_tool(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write retry candidate versions for the bound original candidate."""
    context = get_current_agent_tool_context()
    previous_candidate_id = context.require_candidate_id()
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        record = _candidate_record(context, candidate)
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.setdefault("previous_candidate_id", previous_candidate_id)
        record["metadata"] = metadata
        records.append(record)
    return get_memgraph_query_service().store_edge_candidates(
        context.require_job_id(),
        records,
    )


def _candidate_record(
    context: AgentToolContext,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    record = dict(candidate)
    record.setdefault("job_id", context.job_id)
    if context.chunk_id:
        record.setdefault("source_chunk_id", context.chunk_id)
    return record
