from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit, safe_identifier


def graph_traverse(
    node_id: str,
    id_property: str = "id",
    max_depth: int = 2,
    max_rows: int = 50,
) -> dict[str, Any]:
    depth = max(1, min(max_depth, 4))
    limit = bounded_limit(max_rows)
    property_name = safe_identifier(id_property)
    query = f"""
    MATCH path = (start {{{property_name}: $node_id}})-[*1..{depth}]-(neighbor)
    RETURN path
    LIMIT $limit
    """
    return get_memgraph_bolt_client().execute_read(
        query,
        {"node_id": node_id, "limit": limit},
    )
