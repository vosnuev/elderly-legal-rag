from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.instructions import GRAPH_SCHEMA_INSTRUCTIONS
from settings import settings


class SchemaQueryMethods:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def schema_read(self) -> dict[str, Any]:
        labels = self._client.execute_read(
            """
            MATCH (n)
            UNWIND labels(n) AS label
            RETURN label, count(*) AS count
            ORDER BY label
            """
        )
        relationships = self._client.execute_read(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, count(*) AS count
            ORDER BY relationship_type
            """
        )
        vector_indexes = self._client.execute_read(
            "CALL vector_search.show_index_info() YIELD * RETURN *"
        )
        text_indexes = self._client.execute_read("SHOW INDEX INFO")

        return {
            "instructions": GRAPH_SCHEMA_INSTRUCTIONS.strip(),
            "labels": labels["rows"],
            "relationship_types": relationships["rows"],
            "vector_indexes": vector_indexes["rows"],
            "text_indexes": text_indexes["rows"],
            "query_limits": {
                "max_rows": settings.query_max_rows,
                "timeout_ms": settings.query_timeout_ms,
            },
        }
