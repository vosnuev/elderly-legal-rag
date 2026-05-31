from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit
from settings import settings


def text_search(
    keyword: str,
    top_k: int = 20,
    index_name: str | None = None,
) -> dict[str, Any]:
    limit = bounded_limit(top_k)
    query = """
    CALL text_search.search($index_name, $search_query, $limit)
    YIELD node, score
    RETURN labels(node) AS labels, node AS node, score
    ORDER BY score DESC
    """
    return get_memgraph_bolt_client().execute_read(
        query,
        {
            "index_name": index_name or settings.text_search_index_name,
            "search_query": keyword,
            "limit": limit,
        },
    )
