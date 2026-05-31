from __future__ import annotations

from typing import Any

from langchain.tools import tool

from query.utils import graph_properties
from query.write import write_query
from tools.context import AgentToolContext, get_current_agent_tool_context


@tool
def write_relationship_candidate_tool(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write relationship candidates for pending human review."""
    context = get_current_agent_tool_context()
    return _write_candidates(
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
    return _write_candidates(context.require_job_id(), records)


def _candidate_record(
    context: AgentToolContext,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    record = dict(candidate)
    record.setdefault("job_id", context.job_id)
    if context.chunk_id:
        record.setdefault("source_chunk_id", context.chunk_id)
    return record


def _write_candidates(
    job_id: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    if not candidates:
        return {"stored_count": 0}
    return write_query(
        """
        UNWIND $candidates AS candidate
        MERGE (rc:RelationshipCandidate {id: candidate.id})
        SET rc += candidate,
            rc.job_id = $job_id,
            rc.status = coalesce(candidate.status, "pending_review")
        WITH rc, candidate
        OPTIONAL MATCH (source {id: candidate.source_node})
        OPTIONAL MATCH (target {id: candidate.target_node})
        FOREACH (_ IN CASE WHEN source IS NULL THEN [] ELSE [1] END |
            MERGE (source)-[:HAS_RELATIONSHIP_CANDIDATE]->(rc)
        )
        FOREACH (_ IN CASE WHEN target IS NULL THEN [] ELSE [1] END |
            MERGE (rc)-[:CANDIDATE_TARGET]->(target)
        )
        RETURN count(rc) AS stored_count,
               count(source) AS linked_source_count,
               count(target) AS linked_target_count
        """,
        {
            "job_id": job_id,
            "candidates": [
                graph_properties(candidate)
                for candidate in candidates
            ],
        },
    )
