from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.utils import bounded_limit
from settings import settings


class TextSearchQueryMethods:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def text_search(
        self,
        keyword: str,
        top_k: int = 20,
        index_name: str | None = None,
    ) -> dict[str, Any]:
        limit = bounded_limit(top_k)
        query = """
        CALL text_search.search($index_name, $search_query)
        YIELD node, score
        RETURN labels(node) AS labels, node AS node, score
        ORDER BY score DESC
        LIMIT $limit
        """
        return self._client.execute_read(
            query,
            {
                "index_name": index_name or settings.text_search_index_name,
                "search_query": keyword,
                "limit": limit,
            },
        )

    def keyword_search(self, keyword: str, top_k: int = 20) -> dict[str, Any]:
        return self.text_search(keyword, top_k)
