from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.utils import bounded_limit


class VectorSearchQueryMethods:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def vector_search(
        self,
        index_name: str,
        embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        limit = bounded_limit(top_k)
        query = """
        CALL vector_search.search($index_name, $limit, $embedding)
        YIELD node, similarity, distance
        RETURN node, similarity, distance
        ORDER BY similarity DESC
        """
        return self._client.execute_read(
            query,
            {
                "index_name": index_name,
                "limit": limit,
                "embedding": embedding,
            },
        )
