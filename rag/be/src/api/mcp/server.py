from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from query.read import (
    graph_traverse,
    read_query,
    schema_read,
    text_search,
    vector_search,
)

MCP_INSTRUCTIONS = "External Memgraph tools are read-only."


def _new_mcp(name: str) -> FastMCP:
    return FastMCP(
        name,
        instructions=MCP_INSTRUCTIONS,
        json_response=True,
        stateless_http=True,
        streamable_http_path="/",
    )


def create_external_mcp() -> FastMCP:
    mcp = _new_mcp("SKN28 RAG External Memgraph Tools")
    _register_read_tools(mcp)
    return mcp


def _register_read_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="memgraph.read_query",
        description="Execute a validated read-only Cypher query against Memgraph.",
    )
    def memgraph_read_query(
        query: str,
        parameters: dict[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        return read_query(query, parameters, max_rows)

    @mcp.tool(
        name="memgraph.vector_search",
        description=(
            "Run Memgraph vector_search.search over a vector index. "
            "The caller must provide the query embedding."
        ),
    )
    def memgraph_vector_search(
        index_name: str,
        embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        return vector_search(index_name, embedding, top_k)

    @mcp.tool(
        name="memgraph.text_search",
        description="Search text-bearing graph nodes with the configured text search wrapper.",
    )
    def memgraph_text_search(
        keyword: str,
        top_k: int = 20,
        index_name: str | None = None,
    ) -> dict[str, Any]:
        return text_search(keyword, top_k, index_name)

    @mcp.tool(
        name="memgraph.graph_traverse",
        description="Traverse a bounded graph neighborhood from a node id property.",
    )
    def memgraph_graph_traverse(
        node_id: str,
        id_property: str = "id",
        max_depth: int = 2,
        max_rows: int = 50,
    ) -> dict[str, Any]:
        return graph_traverse(node_id, id_property, max_depth, max_rows)

    @mcp.tool(
        name="memgraph.schema_read",
        description="Read current graph labels, relationship types, and vector index info.",
    )
    def memgraph_schema_read() -> dict[str, Any]:
        return schema_read()
