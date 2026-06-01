from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit
from settings import settings


def list_workspace_documents(limit: int = 100) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (document:Document)
        RETURN document
        ORDER BY document.entry_number DESC, document.created_at DESC
        LIMIT $limit
        """,
        {"limit": bounded_limit(limit)},
    )


def list_documents(limit: int = 100) -> dict[str, Any]:
    return list_workspace_documents(limit)


def search_documents(keyword: str, top_k: int = 20) -> dict[str, Any]:
    query = """
    CALL text_search.search($index_name, $search_query, $limit)
    YIELD node, score
    WITH node, score
    WHERE "Document" IN labels(node)
    RETURN node AS document, score
    ORDER BY score DESC
    """
    return get_memgraph_bolt_client().execute_read(
        query,
        {
            "index_name": settings.document_text_search_index_name,
            "search_query": keyword,
            "limit": bounded_limit(top_k),
        },
    )
