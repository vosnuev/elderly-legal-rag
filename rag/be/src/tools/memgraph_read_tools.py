from __future__ import annotations

from typing import Any

from langchain.tools import tool
from langchain_core.tools import BaseTool

from query.read import (
    graph_traverse,
    read_query,
    schema_read,
    text_search,
    vector_search,
)


@tool
def memgraph_read_query(
    query: str,
    parameters: dict[str, Any] | None = None,
    max_rows: int | None = None,
) -> dict[str, Any]:
    """Execute a bounded read-only Cypher query against Memgraph."""
    return read_query(query, parameters, max_rows)


@tool
def memgraph_schema_read() -> dict[str, Any]:
    """Read graph labels, relationship types, indexes, and query instructions."""
    return schema_read()


@tool
def memgraph_text_search(
    keyword: str,
    top_k: int = 20,
    index_name: str | None = None,
) -> dict[str, Any]:
    """Search indexed text in Memgraph using the configured text search wrapper."""
    return text_search(keyword, top_k, index_name)


@tool
def memgraph_vector_search(
    index_name: str,
    embedding: list[float],
    top_k: int = 5,
) -> dict[str, Any]:
    """Run Memgraph vector search over a configured vector index."""
    return vector_search(index_name, embedding, top_k)


@tool
def memgraph_graph_traverse(
    node_id: str,
    id_property: str = "id",
    max_depth: int = 2,
    max_rows: int = 50,
) -> dict[str, Any]:
    """Traverse a bounded graph neighborhood from a node id property."""
    return graph_traverse(
        node_id,
        id_property,
        max_depth,
        max_rows,
    )


@tool
def memgraph_probe_existing_context(
    keyword: str,
    top_k: int = 20,
) -> dict[str, Any]:
    """Probe existing graph context with primitive read methods."""
    return {
        "text_matches": text_search(keyword, top_k),
        "schema": schema_read(),
    }


MEMGRAPH_READ_TOOLS: list[BaseTool] = [
    memgraph_read_query,
    memgraph_schema_read,
    memgraph_text_search,
    memgraph_vector_search,
    memgraph_graph_traverse,
    memgraph_probe_existing_context,
]
