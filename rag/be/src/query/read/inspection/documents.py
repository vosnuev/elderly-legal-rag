from __future__ import annotations

from query.read.inspection.nodes import read_node_by_id


def read_document_by_id(document_id: str) -> dict[str, object]:
    return read_node_by_id(document_id, label="Document")


def get_document_record(document_id: str) -> dict[str, object]:
    return read_document_by_id(document_id)


def get_document_raw_content(document_id: str) -> str:
    return str(read_document_by_id(document_id).get("raw_content") or "")
