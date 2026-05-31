from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import graph_properties


def register_document(document: dict[str, Any]) -> dict[str, Any]:
    document_id = str(document.get("id") or "").strip()
    if not document_id:
        raise ValueError("document.id is required.")

    query = """
    MERGE (document:Document {id: $document_id})
    ON CREATE SET document.created_at = localDateTime()
    SET document += $document,
        document.updated_at = localDateTime()
    RETURN document.id AS document_id
    """
    return get_memgraph_bolt_client().execute_write(
        query,
        {
            "document_id": document_id,
            "document": graph_properties(document),
        },
    )
