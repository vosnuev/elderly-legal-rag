from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.utils import bounded_limit, safe_identifier


class GraphTraversalQueryMethods:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def graph_traverse(
        self,
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
        return self._client.execute_read(
            query,
            {"node_id": node_id, "limit": limit},
        )
