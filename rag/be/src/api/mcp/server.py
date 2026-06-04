from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from observability.logger import bind_logger
from query.read.core import read_query, schema_read
from query.read.discovery import graph_traverse, text_search, vector_search
from query.utils import bounded_limit
from settings import settings
from tools.agent_output_sanitize import sanitize_agent_tool_output

MCP_INSTRUCTIONS = "External Memgraph tools are read-only."
_logger = bind_logger(component="external_mcp")
_PREVIEW_TEXT_LIMIT = 240

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
        host=settings.mcp_host,
        port=settings.mcp_port,
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
            "Use this to answer Korean law, policy, welfare, employment, and "
            "document-grounded user questions from the SKN28 RAG Memgraph graph. "
            "Write only read-only Cypher. Prefer concise queries that return "
            "answer evidence plus source-identifying fields such as id, file_name, "
            "title, article, content, evidence_text, or raw_content excerpts."
        ),
    )
    def memgraph_read_query(
        query: str,
        parameters: dict[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        return _run_logged_mcp_tool(
            "memgraph.read_query",
            {
                "query_preview": _text_preview(query),
                "has_parameters": bool(parameters),
                "parameter_keys": sorted(parameters) if parameters else [],
                "max_rows": max_rows,
            },
            lambda: sanitize_agent_tool_output(
                _execute_mcp_read_query(query, parameters, max_rows)
            ),
        )

    @mcp.tool(
        name="memgraph.vector_search",
        description=(
            "Run Memgraph vector_search.search over a vector index only when the "
            "caller already has a numeric embedding vector. Do not use this for a "
            "plain natural-language user question unless an embedding was provided."
        ),
    )
    def memgraph_vector_search(
        index_name: str,
        embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        return _run_logged_mcp_tool(
            "memgraph.vector_search",
            {
                "index_name": index_name,
                "embedding_length": len(embedding),
                "top_k": top_k,
            },
            lambda: sanitize_agent_tool_output(
                vector_search(index_name, embedding, top_k)
            ),
        )

    @mcp.tool(
        name="memgraph.text_index_search",
        description=(
            "Use this first for plain Korean keywords, law names, article names, "
            "policy names, regions, institutions, and document titles. It searches "
            "configured Memgraph text indexes and returns candidate graph nodes "
            "that should be followed by memgraph.graph_traverse or memgraph.read_query "
            "to inspect connected chunks, documents, relationships, and review notes. "
            "Do not repeatedly call this with small keyword variants when an anchor "
            "node id is already available; expand the graph from the anchor instead. "
            "If the configured text index is missing, the server falls back to a "
            "bounded read-only property CONTAINS scan."
        ),
    )
    def memgraph_text_index_search(
        keyword: str,
        top_k: int = 20,
        index_name: str | None = None,
    ) -> dict[str, Any]:
        return _run_logged_mcp_tool(
            "memgraph.text_index_search",
            {
                "keyword_preview": _text_preview(keyword),
                "top_k": top_k,
                "index_name": index_name,
            },
            lambda: sanitize_agent_tool_output(
                text_search(keyword, top_k, index_name)
            ),
        )

    @mcp.tool(
        name="memgraph.graph_traverse",
        description=(
            "Use this after finding a relevant node id to inspect nearby chunks, "
            "documents, entities, review notes, and relationships. Prefer this over "
            "repeating keyword searches when you need related context around an "
            "already found chunk or document. Keep traversal bounded and use the "
            "result as evidence for the final answer."
        ),
    )
    def memgraph_graph_traverse(
        node_id: str,
        id_property: str = "id",
        max_depth: int = 2,
        max_rows: int = 50,
    ) -> dict[str, Any]:
        return _run_logged_mcp_tool(
            "memgraph.graph_traverse",
            {
                "node_id": node_id,
                "id_property": id_property,
                "max_depth": max_depth,
                "max_rows": max_rows,
            },
            lambda: sanitize_agent_tool_output(
                graph_traverse(node_id, id_property, max_depth, max_rows)
            ),
        )

    @mcp.tool(
        name="memgraph.schema_read",
        description=(
            "Use this when you need to understand the available Memgraph labels, "
            "relationship types, properties, and indexes before writing a Cypher "
            "query or choosing another RAG tool."
        ),
    )
    def memgraph_schema_read() -> dict[str, Any]:
        return _run_logged_mcp_tool(
            "memgraph.schema_read",
            {},
            lambda: sanitize_agent_tool_output(schema_read()),
        )


def _run_logged_mcp_tool(
    tool_name: str,
    input_summary: dict[str, Any],
    call: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    started_at = time.perf_counter()
    logger = _logger.bind(tool_name=tool_name, input_summary=input_summary)
    logger.info("MCP tool invocation started")
    try:
        result = call()
    except Exception:
        logger.bind(duration_ms=_elapsed_ms(started_at)).exception(
            "MCP tool invocation failed"
        )
        raise

    logger.bind(
        duration_ms=_elapsed_ms(started_at),
        result_summary=_result_summary(result),
    ).info("MCP tool invocation completed")
    return result


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)


def _result_summary(result: dict[str, Any]) -> dict[str, Any]:
    rows = result.get("rows")
    return {
        "row_count": result.get("row_count"),
        "returned_row_count": result.get(
            "returned_row_count",
            len(rows) if isinstance(rows, list) else None,
        ),
        "truncated_rows": result.get("truncated_rows"),
        "sanitized": result.get("sanitized"),
        "keys": sorted(result),
    }


def _text_preview(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) <= _PREVIEW_TEXT_LIMIT:
        return compact
    return f"{compact[:_PREVIEW_TEXT_LIMIT]}...<truncated chars={len(compact) - _PREVIEW_TEXT_LIMIT}>"


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
