from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit, node_properties, safe_identifier
from settings import settings


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


def get_document_record(document_id: str) -> dict[str, Any]:
    return read_node_by_id(document_id, label="Document")


def get_document_raw_content(document_id: str) -> str:
    return str(get_document_record(document_id).get("raw_content") or "")


def list_documents(limit: int = 100) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (document:Document)
        RETURN document
        ORDER BY document.entry_number DESC, document.created_at DESC
        LIMIT $limit
        """,
        {"limit": bounded_limit(limit)},
    )


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
