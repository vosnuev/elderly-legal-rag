from __future__ import annotations

from typing import Any, Literal

from langchain.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from query.read.inspection import read_node_by_id
from query.write import write_relationship_candidates


class EdgeCandidateWriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_node: str = Field(
        min_length=1,
        description="Existing Memgraph node id for the left endpoint of the proposed edge.",
    )
    right_node: str = Field(
        min_length=1,
        description="Existing Memgraph node id for the right endpoint of the proposed edge.",
    )
    relationship_type: str = Field(
        min_length=1,
        description="Proposed relationship type to materialize after reviewer approval.",
    )
    relationship_direction: Literal[
        "left_to_right",
        "right_to_left",
        "bidirectional",
    ] = Field(
        default="left_to_right",
        description=(
            "Materialization direction: left_to_right, right_to_left, or bidirectional."
        ),
    )
    evidence_text: str = Field(
        min_length=1,
        description="Short source evidence text that grounds this proposed relationship.",
    )
    rationale: str = Field(
        min_length=1,
        description="Korean explanation of why this relationship should be reviewed.",
    )
    evidence_node_id: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Optional Document, Chunk, or graph node id that grounds this proposed edge "
            "when the relationship is stated by a separate evidence node."
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional non-runtime metadata such as external evidence urls or confidence.",
    )


class WriteEdgeCandidatesToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[EdgeCandidateWriteInput] = Field(
        min_length=1,
        description="Relationship edge candidates to write for pending human review.",
    )


## above schema, below tools

@tool(args_schema=WriteEdgeCandidatesToolInput)
def write_relationship_candidate_tool(
    candidates: list[EdgeCandidateWriteInput],
) -> dict[str, Any]:
    """Write relationship candidates for pending human review.

    Endpoints must be existing DB node ids verified by read tools. This tool
    creates RelationshipCandidate review artifacts, not final graph edges.
    """
    return write_relationship_candidates(
        [_candidate_record(candidate) for candidate in candidates]
    )


def _candidate_record(candidate: EdgeCandidateWriteInput | dict[str, Any]) -> dict[str, Any]:
    record = _candidate_payload(candidate)
    record.setdefault("job_id", _candidate_job_id_from_nodes(record))
    return record


def _candidate_payload(
    candidate: EdgeCandidateWriteInput | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(candidate, EdgeCandidateWriteInput):
        return candidate.model_dump()
    return EdgeCandidateWriteInput.model_validate(candidate).model_dump()


def _candidate_job_id_from_nodes(candidate: dict[str, Any]) -> str:
    for node_id in (
        candidate.get("evidence_node_id"),
        candidate.get("left_node"),
        candidate.get("right_node"),
    ):
        if node_id:
            job_id = _node_job_id(str(node_id))
            if job_id:
                return job_id
    return ""


def _node_job_id(node_id: str) -> str:
    try:
        node = read_node_by_id(node_id)
    except ValueError:
        return ""
    metadata = node.get("metadata")
    if isinstance(metadata, dict):
        metadata_job_id = str(metadata.get("last_ingest_job_id") or "")
        if metadata_job_id:
            return metadata_job_id
    # Chunk.last_ingest_job_id is stored as a top-level property by the chunk
    # write query. Do not stop at empty metadata, otherwise RelationshipCandidate
    # nodes lose their job provenance and disappear from job-scoped status counts.
    return str(node.get("last_ingest_job_id") or "")
