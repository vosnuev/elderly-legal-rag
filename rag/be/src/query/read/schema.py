from __future__ import annotations

import json
from typing import Any

from external.memgraph import get_memgraph_bolt_client
from settings import settings


def schema_read() -> dict[str, Any]:
    schema_result = get_memgraph_bolt_client().execute_read("SHOW SCHEMA INFO")
    schema = _parse_schema_info(schema_result)

    return {
        "source": "SHOW SCHEMA INFO",
        "schema": schema,
        "nodes": schema.get("nodes", []),
        "edges": schema.get("edges", []),
        "node_indexes": schema.get("node_indexes", []),
        "edge_indexes": schema.get("edge_indexes", []),
        "node_constraints": schema.get("node_constraints", []),
        "enums": schema.get("enums", []),
        "query_limits": {
            "max_rows": settings.query_max_rows,
            "timeout_ms": settings.query_timeout_ms,
        },
    }


def _parse_schema_info(schema_result: dict[str, Any]) -> dict[str, Any]:
    rows = schema_result.get("rows", [])
    if not rows:
        raise ValueError("SHOW SCHEMA INFO returned no rows.")

    schema_value = rows[0].get("schema")
    if isinstance(schema_value, str):
        parsed = json.loads(schema_value)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("SHOW SCHEMA INFO returned non-object JSON.")

    if isinstance(schema_value, dict):
        return schema_value

    raise ValueError("SHOW SCHEMA INFO returned an invalid schema value.")
