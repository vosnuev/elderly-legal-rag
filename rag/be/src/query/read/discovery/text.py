from __future__ import annotations

from typing import Any

from neo4j.exceptions import Neo4jError

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
    parameters = {
        "index_name": index_name or settings.text_search_index_name,
        "search_query": keyword,
        "limit": limit,
    }
    try:
        return get_memgraph_bolt_client().execute_read(query, parameters)
    except Neo4jError as error:
        if not _is_missing_text_index_error(error):
            raise
        result = _fallback_contains_node_search(keyword, limit)
        result["search_mode"] = "contains_scan"
        result["missing_text_index"] = parameters["index_name"]
        return result


def text_search_edges(
    keyword: str,
    top_k: int = 20,
    index_name: str | None = None,
) -> dict[str, Any]:
    limit = bounded_limit(top_k)
    query = """
    CALL text_search.search_edges($index_name, $search_query, $limit)
    YIELD edge, score
    RETURN type(edge) AS relationship_type, edge AS edge, score
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


def _is_missing_text_index_error(error: Neo4jError) -> bool:
    message = str(error)
    return "text_search.search" in message and "doesn't exist" in message


def _fallback_contains_node_search(keyword: str, limit: int) -> dict[str, Any]:
    query = """
    MATCH (node)
    WITH
      node,
      labels(node) AS labels,
      coalesce(node.file_name, '') + ' ' +
      coalesce(node.title, '') + ' ' +
      coalesce(node.article, '') + ' ' +
      coalesce(node.name, '') + ' ' +
      coalesce(node.id, '') + ' ' +
      coalesce(node.law_id, '') + ' ' +
      coalesce(node.content, '') + ' ' +
      coalesce(node.text, '') + ' ' +
      coalesce(node.evidence_text, '') + ' ' +
      coalesce(node.raw_content, '') AS matched_text
    WHERE toLower(matched_text) CONTAINS toLower($search_query)
    RETURN
      labels,
      node,
      matched_text,
      1.0 AS score
    LIMIT $limit
    """
    return get_memgraph_bolt_client().execute_read(
        query,
        {
            "search_query": keyword,
            "limit": limit,
        },
    )
