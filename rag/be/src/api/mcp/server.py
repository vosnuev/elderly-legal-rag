from __future__ import annotations

import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from query.read.core import read_query, schema_read
from query.read.discovery import graph_traverse, text_search, vector_search
from query.utils import bounded_limit

MCP_INSTRUCTIONS = "External Memgraph tools are read-only."

_FORBIDDEN_CYPHER_OPERATION = re.compile(
    r"\b("
    r"CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|ALTER|RENAME|"
    r"GRANT|DENY|REVOKE|FOREACH|LOAD\s+CSV"
    r")\b",
    re.IGNORECASE,
)
_FORBIDDEN_PROCEDURE = re.compile(
    r"\bCALL\s+("
    r"dbms\b|"
    r"apoc\.(create|merge|delete|refactor|periodic|load|export|schema)\b"
    r")",
    re.IGNORECASE,
)


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
        description=(
            "Execute a bounded, write-restricted read Cypher query against Memgraph."
        ),
    )
    def memgraph_read_query(
        query: str,
        parameters: dict[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        return _execute_mcp_read_query(query, parameters, max_rows)

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
        name="memgraph.text_index_search",
        description=(
            "Search graph nodes through a configured Memgraph text index. "
            "This is not a substring CONTAINS scan and requires the index to exist."
        ),
    )
    def memgraph_text_index_search(
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


def _execute_mcp_read_query(
    query: str,
    parameters: dict[str, Any] | None,
    max_rows: int | None,
) -> dict[str, Any]:
    _validate_mcp_read_query(query)
    return read_query(query, parameters, bounded_limit(max_rows))


def _validate_mcp_read_query(query: str) -> None:
    normalized = _remove_cypher_literals_and_comments(query)
    if _FORBIDDEN_CYPHER_OPERATION.search(normalized):
        raise ValueError("MCP memgraph.read_query only accepts read-only Cypher.")
    if _FORBIDDEN_PROCEDURE.search(normalized):
        raise ValueError(
            "MCP memgraph.read_query does not allow write-capable procedures."
        )


def _remove_cypher_literals_and_comments(query: str) -> str:
    output: list[str] = []
    index = 0
    length = len(query)
    quote: str | None = None

    while index < length:
        char = query[index]
        next_char = query[index + 1] if index + 1 < length else ""

        if quote is not None:
            if char == "\\":
                index += 2
                output.append(" ")
                continue
            if char == quote:
                quote = None
            output.append(" ")
            index += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            output.append(" ")
            index += 1
            continue

        if char == "/" and next_char == "/":
            while index < length and query[index] not in "\r\n":
                output.append(" ")
                index += 1
            continue

        if char == "/" and next_char == "*":
            output.extend("  ")
            index += 2
            while index + 1 < length and not (
                query[index] == "*" and query[index + 1] == "/"
            ):
                output.append(" ")
                index += 1
            if index + 1 < length:
                output.extend("  ")
                index += 2
            continue

        output.append(char)
        index += 1

    return "".join(output)
