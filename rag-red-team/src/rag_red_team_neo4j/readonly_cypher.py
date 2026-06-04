from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from neo4j import Driver, RoutingControl
from neo4j.graph import Node, Path, Relationship


WRITE_KEYWORDS = {
    "ALTER",
    "CALL",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "FOREACH",
    "LOAD",
    "MERGE",
    "REMOVE",
    "SET",
    "USE",
}
READ_START_KEYWORDS = {
    "EXPLAIN",
    "MATCH",
    "OPTIONAL",
    "PROFILE",
    "RETURN",
    "SHOW",
    "UNWIND",
    "WITH",
}
LINE_COMMENT_RE = re.compile(r"//.*?$", re.MULTILINE)
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
TOKEN_RE = re.compile(r"\b[A-Z_]+\b")


class ReadOnlyCypherError(ValueError):
    """Raised when a Cypher statement is not allowed by the read-only guard."""


def _strip_comments(query: str) -> str:
    without_blocks = BLOCK_COMMENT_RE.sub(" ", query)
    return LINE_COMMENT_RE.sub(" ", without_blocks)


def validate_readonly_cypher(query: str) -> str:
    sanitized = _strip_comments(query).strip()
    if not sanitized:
        raise ReadOnlyCypherError("Query is empty.")

    if ";" in sanitized.rstrip(";"):
        raise ReadOnlyCypherError("Only one Cypher statement is allowed.")
    sanitized = sanitized.rstrip(";").strip()

    tokens = TOKEN_RE.findall(sanitized.upper())
    if not tokens:
        raise ReadOnlyCypherError("Query does not contain Cypher keywords.")

    blocked = sorted(WRITE_KEYWORDS.intersection(tokens))
    if blocked:
        raise ReadOnlyCypherError(
            f"Read-only MCP blocks these Cypher keyword(s): {', '.join(blocked)}"
        )

    if tokens[0] not in READ_START_KEYWORDS:
        raise ReadOnlyCypherError(
            "Read-only query must start with MATCH, OPTIONAL MATCH, RETURN, WITH, "
            "UNWIND, SHOW, EXPLAIN, or PROFILE."
        )

    return sanitized


def serialize_value(value: Any) -> Any:
    if isinstance(value, Node):
        return {
            "element_id": value.element_id,
            "labels": sorted(value.labels),
            "properties": dict(value),
        }
    if isinstance(value, Relationship):
        return {
            "element_id": value.element_id,
            "type": value.type,
            "start_node": value.start_node.element_id,
            "end_node": value.end_node.element_id,
            "properties": dict(value),
        }
    if isinstance(value, Path):
        return {
            "nodes": [serialize_value(node) for node in value.nodes],
            "relationships": [serialize_value(rel) for rel in value.relationships],
        }
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    return value


def run_read_query(
    driver: Driver,
    database: str,
    query: str,
    parameters: dict[str, Any] | None = None,
    max_rows: int = 100,
) -> dict[str, Any]:
    safe_query = validate_readonly_cypher(query)
    row_limit = max(1, min(max_rows, 500))

    result = driver.execute_query(
        safe_query,
        parameters_=parameters or {},
        database_=database,
        routing_=RoutingControl.READ,
    )
    rows = [
        {key: serialize_value(record.get(key)) for key in result.keys}
        for record in result.records[:row_limit]
    ]
    return {
        "query": safe_query,
        "parameters": parameters or {},
        "row_count": len(rows),
        "truncated": len(result.records) > row_limit,
        "keys": list(result.keys),
        "rows": rows,
    }

