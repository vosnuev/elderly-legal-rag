from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit


def read_query(
    query: str,
    parameters: dict[str, Any] | None = None,
    max_rows: int | None = None,
) -> dict[str, Any]:
    bounded_query = (
        _append_limit(query, bounded_limit(max_rows))
        if max_rows is not None
        else query
    )
    result = get_memgraph_bolt_client().execute_read(bounded_query, parameters)
    result["access"] = "read"
    return result


def _append_limit(query: str, limit: int) -> str:
    normalized = query.strip().removesuffix(";").strip()
    lowered = normalized.lower()
    if " limit " in f" {lowered} " or lowered.startswith("show "):
        return normalized
    if " return " not in f" {lowered} " and " yield " not in f" {lowered} ":
        return normalized
    return f"{normalized} LIMIT {limit}"
