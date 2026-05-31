from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.read.discovery.traversal import graph_traverse
from query.utils import node_properties, safe_identifier


def read_node_by_id(
    node_id: str,
    id_property: str = "id",
    label: str | None = None,
) -> dict[str, Any]:
    label_clause = f":{safe_identifier(label)}" if label else ""
    property_name = safe_identifier(id_property)
    query = f"""
    MATCH (node{label_clause} {{{property_name}: $node_id}})
    RETURN node
    LIMIT 1
    """
    result = get_memgraph_bolt_client().execute_read(query, {"node_id": node_id})
    if not result["rows"]:
        raise ValueError(f"Node not found: {node_id}")
    return node_properties(result["rows"][0]["node"])


def read_nodes_by_ids(
    node_ids: list[str],
    id_property: str = "id",
    label: str | None = None,
) -> dict[str, Any]:
    label_clause = f":{safe_identifier(label)}" if label else ""
    property_name = safe_identifier(id_property)
    query = f"""
    MATCH (node{label_clause})
    WHERE node.{property_name} IN $node_ids
    RETURN node
    """
    return get_memgraph_bolt_client().execute_read(query, {"node_ids": node_ids})


def read_node_neighborhood(
    node_id: str,
    id_property: str = "id",
    max_depth: int = 2,
    max_rows: int = 50,
) -> dict[str, Any]:
    return graph_traverse(
        node_id=node_id,
        id_property=id_property,
        max_depth=max_depth,
        max_rows=max_rows,
    )
