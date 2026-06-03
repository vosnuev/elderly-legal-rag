from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit


def vector_search(
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
    return get_memgraph_bolt_client().execute_read(
        query,
        {
            "index_name": index_name,
            "limit": limit,
            "embedding": embedding,
        },
    )


def vector_search_edges(
    index_name: str,
    embedding: list[float],
    top_k: int = 5,
) -> dict[str, Any]:
    limit = bounded_limit(top_k)
    query = """
    CALL vector_search.search_edges($index_name, $limit, $embedding)
    YIELD edge, similarity, distance
    RETURN edge, similarity, distance
    ORDER BY similarity DESC
    """
    return get_memgraph_bolt_client().execute_read(
        query,
        {
            "index_name": index_name,
            "limit": limit,
            "embedding": embedding,
        },
    )
