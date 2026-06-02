# 역할: agent가 자유형 Memory 문서를 읽거나 append할 때 사용하는 tool wrapper이다.
from __future__ import annotations

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from query.read.inspection import list_memory
from query.write import append_memory_entry
from tools.agent_output_sanitize import sanitize_agent_tool_output


class ReadMemoryToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str | None = Field(
        default="global",
        description="Memory scope. The default reads the single shared memory document.",
    )
    status: str | None = Field(
        default="active",
        description="Memory status filter.",
    )


class AppendMemoryToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry: str = Field(
        min_length=1,
        description="Free-form markdown/text entry to append at the bottom of Memory.content.",
    )
    scope: str = Field(
        default="global",
        min_length=1,
        description="Memory scope. Use the default shared memory unless a workflow owns a separate scope.",
    )
    title: str = Field(
        default="Reviewer feedback memory",
        min_length=1,
        description="Memory document title used when creating the Memory node.",
    )
    source_review_note_id: str | None = Field(
        default=None,
        min_length=1,
        description="Optional ReviewNote node id to link as feedback provenance.",
    )
    source_candidate_id: str | None = Field(
        default=None,
        min_length=1,
        description="Optional RelationshipCandidate id when no ReviewNote node is available.",
    )


@tool(args_schema=ReadMemoryToolInput)
def read_memory_tool(
    scope: str | None = "global",
    status: str | None = "active",
) -> dict[str, Any]:
    """Read the shared append-only Memory document used by agents."""
    return sanitize_agent_tool_output(
        list_memory(
            scope=scope,
            status=status,
            limit=1,
        )
    )


@tool(args_schema=AppendMemoryToolInput)
def append_memory_tool(
    entry: str,
    scope: str = "global",
    title: str = "Reviewer feedback memory",
    source_review_note_id: str | None = None,
    source_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Append a free-form entry to Memory and optionally link source feedback."""
    return append_memory_entry(
        entry=entry,
        scope=scope,
        title=title,
        source_review_note_id=source_review_note_id,
        source_candidate_id=source_candidate_id,
        author="append_memory_tool",
    )
