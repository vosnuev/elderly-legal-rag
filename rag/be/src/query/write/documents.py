from __future__ import annotations

from typing import Any

from query.schema import DocumentNode
from query.utils import db_generated_id_expression, graph_properties
from query.write.core import write_query


def register_document(document: DocumentNode | dict[str, Any]) -> dict[str, Any]:
    record = _document_record(document)
    query = f"""
    CREATE (document:Document)
    SET document += $document,
        document.id = {db_generated_id_expression()},
        document.created_at = localDateTime(),
        document.updated_at = localDateTime()
    RETURN document.id AS document_id
    """
    result = write_query(
        query,
        {"document": graph_properties(record)},
    )
    if not result["rows"]:
        raise ValueError("Document registration did not return a document id.")
    return result


def _document_record(document: DocumentNode | dict[str, Any]) -> dict[str, Any]:
    if isinstance(document, DocumentNode):
        record = document.model_dump(exclude_none=True)
    else:
        record = DocumentNode.model_validate(document).model_dump(exclude_none=True)
    record.pop("id", None)
    return record
