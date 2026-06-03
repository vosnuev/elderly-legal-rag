from __future__ import annotations

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from query.read.inspection import (
    get_document_raw_content,
    get_document_record,
    read_chunk_by_id,
)
from query.write import write_chunks_for_document
from tools.agent_output_sanitize import sanitize_agent_tool_output


class ChunkWriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_index: int = Field(
        ge=1,
        description="One-based chunk order inside the source document.",
    )
    chunk_name: str = Field(
        default="",
        description=(
            "Short human-readable display name for this chunk, such as an "
            "article title, section heading, or concise topic label."
        ),
    )
    chunk_description: str = Field(
        default="",
        description=(
            "One or two short human-readable sentences explaining this chunk's "
            "role in the original document."
        ),
    )
    text: str = Field(
        min_length=1,
        description="Exact source text copied from the original document.",
    )
    start_unique_string: str = Field(
        min_length=1,
        description="Boundary marker that appears exactly once in the source document.",
    )
    end_unique_string: str = Field(
        min_length=1,
        description="Ending boundary marker that appears exactly once in the source document.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Short semantic tags assigned to the chunk.",
    )
    summary: str = Field(
        default="",
        description="Short summary of this chunk for reviewer scanning.",
    )
    reason: str = Field(
        default="",
        description="Why this boundary was chosen.",
    )
    start_char: int | None = Field(
        default=None,
        ge=0,
        description="Optional source start character offset.",
    )
    end_char: int | None = Field(
        default=None,
        ge=0,
        description="Optional source end character offset.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional non-runtime chunk metadata.",
    )


class WriteChunkToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(
        min_length=1,
        description="Source Document node id to connect generated chunks to.",
    )
    chunks: list[ChunkWriteInput] = Field(
        min_length=1,
        description="Chunks to write for the source document.",
    )


class CheckDocumentUniqueStringToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(
        min_length=1,
        description="Source Document node id to inspect.",
    )
    text: str = Field(
        min_length=1,
        description="Candidate boundary marker to check inside Document.raw_content.",
    )


class ReadChunkToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(
        min_length=1,
        description="Chunk node id to inspect.",
    )
    include_embedding: bool = Field(
        default=False,
        description="Return the full embedding vector only when vector search needs it.",
    )


class ReadChunkContextToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(
        min_length=1,
        description="Chunk node id to inspect without returning the raw embedding vector.",
    )


@tool
def read_document_tool(document_id: str) -> dict[str, Any]:
    """Read full source Document.raw_content for chunking only."""
    raw_content = get_document_raw_content(document_id)
    return {
        "document_id": document_id,
        "raw_content": raw_content,
        "content_length": len(raw_content),
    }

# Deprecated: LLM-facing read tools should not expose the full embedding vector.
@tool(args_schema=ReadChunkToolInput)
def read_chunk_tool(chunk_id: str, include_embedding: bool = False) -> dict[str, Any]:
    """Read a Chunk node by id; deprecated for LLM agents because embedding can be large."""
    chunk = read_chunk_by_id(chunk_id)
    if not include_embedding:
        chunk.pop("embedding", None)
    return chunk


@tool(args_schema=ReadChunkContextToolInput)
def read_chunk_context_tool(chunk_id: str) -> dict[str, Any]:
    """Read existing Chunk text/name/description/summary/tags without embedding vectors."""
    chunk = read_chunk_by_id(chunk_id)
    # Embedding vectors are large and should stay in deterministic vector-search
    # code paths. LLM agents only need the text, summary, tags, and status fields.
    chunk.pop("embedding", None)
    return sanitize_agent_tool_output(chunk)


@tool
def count_document_occurrences_tool(document_id: str, text: str) -> int:
    """Count exact occurrences of text inside source Document.raw_content."""
    source = get_document_raw_content(document_id)
    return source.count(text)


@tool(args_schema=CheckDocumentUniqueStringToolInput)
def check_document_unique_string_tool(document_id: str, text: str) -> dict[str, Any]:
    """Check whether a boundary marker appears exactly once in source Document.raw_content."""
    source = get_document_raw_content(document_id)
    occurrence_count = source.count(text)
    first_start_char = source.find(text)
    first_end_char = first_start_char + len(text) if first_start_char >= 0 else None
    return {
        "document_id": document_id,
        "is_unique": occurrence_count == 1,
        "occurrence_count": occurrence_count,
        "first_start_char": first_start_char if first_start_char >= 0 else None,
        "first_end_char": first_end_char,
        "text_length": len(text),
    }


@tool(args_schema=WriteChunkToolInput)
def write_chunk_tool(document_id: str, chunks: list[ChunkWriteInput]) -> dict[str, Any]:
    """Write semantic chunks for a source document and return DB-generated chunk ids."""
    job_id = _document_ingest_job_id(document_id)
    return write_chunks_for_document(
        document_id=document_id,
        chunks=[_chunk_record(chunk) for chunk in chunks],
        job_id=job_id,
    )


def _chunk_record(chunk: ChunkWriteInput | dict[str, Any]) -> dict[str, Any]:
    if isinstance(chunk, ChunkWriteInput):
        return chunk.model_dump()
    return ChunkWriteInput.model_validate(chunk).model_dump()


def _document_ingest_job_id(document_id: str) -> str:
    document = get_document_record(document_id)
    metadata = document.get("metadata")
    if isinstance(metadata, dict):
        return str(metadata.get("last_ingest_job_id") or "")
    return ""
