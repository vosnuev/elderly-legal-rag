from __future__ import annotations

from functools import lru_cache
from time import perf_counter
from typing import Any

from neo4j import GraphDatabase, RoutingControl
from neo4j.graph import Node, Path, Relationship

from settings import settings


class MemgraphBoltClient:
    """Pure Bolt adapter for Memgraph query execution."""

    def __init__(
        self,
        uri: str,
        username: str | None,
        password: str | None,
    ) -> None:
        auth = (username or "", password or "")
        self._driver = GraphDatabase.driver(uri, auth=auth)

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    def close(self) -> None:
        self._driver.close()

    def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._execute(query, parameters, RoutingControl.READ)

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._execute(query, parameters, RoutingControl.WRITE)

    def _execute(
        self,
        query: str,
        parameters: dict[str, Any] | None,
        routing: RoutingControl,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        records, summary, keys = self._driver.execute_query(
            query,
            parameters_=_sanitize_parameters(parameters),
            routing_=routing,
            database_="memgraph",
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)

        return {
            "columns": list(keys),
            "rows": [
                {key: _serialize_value(record.get(key)) for key in keys}
                for record in records
            ],
            "row_count": len(records),
            "elapsed_ms": elapsed_ms,
            "query": summary.query,
            "counters": _serialize_counters(summary.counters),
        }


@lru_cache
def get_memgraph_bolt_client() -> MemgraphBoltClient:
    password = (
        settings.memgraph_password.get_secret_value()
        if settings.memgraph_password is not None
        else None
    )
    return MemgraphBoltClient(
        uri=settings.memgraph_uri,
        username=settings.memgraph_username,
        password=password,
    )


def _sanitize_parameters(parameters: dict[str, Any] | None) -> dict[str, Any]:
    if parameters is None:
        return {}
    return parameters


def _serialize_counters(counters: Any) -> dict[str, Any]:
    return {
        "contains_updates": counters.contains_updates,
        "contains_system_updates": counters.contains_system_updates,
        "nodes_created": counters.nodes_created,
        "nodes_deleted": counters.nodes_deleted,
        "relationships_created": counters.relationships_created,
        "relationships_deleted": counters.relationships_deleted,
        "properties_set": counters.properties_set,
        "labels_added": counters.labels_added,
        "labels_removed": counters.labels_removed,
        "indexes_added": counters.indexes_added,
        "indexes_removed": counters.indexes_removed,
        "constraints_added": counters.constraints_added,
        "constraints_removed": counters.constraints_removed,
        "system_updates": counters.system_updates,
    }


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Node):
        return {
            "type": "node",
            "element_id": value.element_id,
            "labels": sorted(value.labels),
            "properties": dict(value),
        }

    if isinstance(value, Relationship):
        return {
            "type": "relationship",
            "element_id": value.element_id,
            "relationship_type": value.type,
            "start_node_id": value.start_node.element_id,
            "end_node_id": value.end_node.element_id,
            "properties": dict(value),
        }

    if isinstance(value, Path):
        return {
            "type": "path",
            "nodes": [_serialize_value(node) for node in value.nodes],
            "relationships": [
                _serialize_value(relationship)
                for relationship in value.relationships
            ],
        }

    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_serialize_value(item) for item in value]

    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]

    return value
