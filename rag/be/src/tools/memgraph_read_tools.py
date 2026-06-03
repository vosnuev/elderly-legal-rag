from __future__ import annotations

from typing import Any

from langchain.tools import tool
from langchain_core.tools import BaseTool

from query.read.core import read_query, schema_read
from query.read.discovery import graph_traverse, text_search, vector_search
from query.utils import bounded_limit
from tools.agent_output_sanitize import sanitize_agent_tool_output

_AGENT_RAW_CYPHER_MAX_ROWS = 20


@tool
def memgraph_read_query(
    query: str,
    parameters: dict[str, Any] | None = None,
    max_rows: int | None = None,
) -> dict[str, Any]:
    """Run a bounded read-only Cypher query for existing graph context.

    Use this to inspect known node ids, candidate endpoints, or small graph
    projections. Do not request Document.raw_content, Chunk.embedding, or
    unbounded result sets.
    """
    # Agent-facing raw Cypher is useful, but its result must not carry full
    # Document.raw_content, Chunk.embedding, or unbounded rows into message state.
    row_limit = min(bounded_limit(max_rows), _AGENT_RAW_CYPHER_MAX_ROWS)
    return sanitize_agent_tool_output(read_query(query, parameters, row_limit))


@tool
def memgraph_schema_read() -> dict[str, Any]:
    """Read current Memgraph labels, relationship types, indexes, and query limits."""
    return schema_read()


@tool
def memgraph_text_index_search(
    keyword: str,
    top_k: int = 20,
    index_name: str | None = None,
) -> dict[str, Any]:
    """Search a prepared Memgraph text index for existing graph anchors.

    This is not a substring scan. If the requested index is not present or the
    keyword has no indexed match, the tool can fail or return no rows.
    """
    return sanitize_agent_tool_output(text_search(keyword, top_k, index_name))


@tool
def memgraph_vector_search(
    index_name: str,
    embedding: list[float],
    top_k: int = 5,
) -> dict[str, Any]:
    """Run vector search over a configured Memgraph vector index.

    Use only when you already have an embedding vector and a known index name.
    This tool does not create embeddings from text.
    """
    return sanitize_agent_tool_output(vector_search(index_name, embedding, top_k))


@tool
def memgraph_graph_traverse(
    node_id: str,
    id_property: str = "id",
    max_depth: int = 2,
    max_rows: int = 50,
) -> dict[str, Any]:
    """Traverse a small bounded neighborhood from an existing node id."""
    return sanitize_agent_tool_output(
        graph_traverse(
            node_id,
            id_property,
            max_depth,
            min(bounded_limit(max_rows), _AGENT_RAW_CYPHER_MAX_ROWS),
        )
    )


MCP_ASSIGNED_MEMGRAPH_TOOLS: list[BaseTool] = [
    memgraph_read_query,
    memgraph_schema_read,
    memgraph_text_index_search,
    memgraph_vector_search,
    memgraph_graph_traverse,
]
