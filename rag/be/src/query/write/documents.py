from __future__ import annotations

from typing import Any

from query.schema import DocumentNode
from query.utils import graph_properties
from query.write.core import write_query


def register_document(document: DocumentNode | dict[str, Any]) -> dict[str, Any]:
    record = _document_record(document)
    query = """
    MERGE (document:Document {id: $document_id})
    ON CREATE SET document.created_at = localDateTime()
    SET document += $document,
        document.updated_at = localDateTime()
    RETURN document.id AS document_id
    """
    result = write_query(
        query,
        {
            "document_id": record["id"],
            "document": graph_properties(record),
        },
    )
    if not result["rows"]:
        raise ValueError("Document registration did not return a document id.")
    return result


def _document_record(document: DocumentNode | dict[str, Any]) -> dict[str, Any]:
    if isinstance(document, DocumentNode):
        return document.model_dump()
    return DocumentNode.model_validate(document).model_dump()
