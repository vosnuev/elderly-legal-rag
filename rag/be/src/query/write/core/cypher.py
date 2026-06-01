from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client


def write_query(
    query: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = get_memgraph_bolt_client().execute_write(query, parameters)
    result["access"] = "write"
    return result
