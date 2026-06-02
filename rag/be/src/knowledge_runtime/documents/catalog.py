"""Document list and search projection boundary for FE views."""

from __future__ import annotations

from knowledge_runtime.schemas import (
    DocumentSummary,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from query.read.runtime import list_documents, search_documents
from settings import settings


class DocumentCatalog:
    def list_documents(self) -> list[DocumentSummary]:
        result = list_documents(limit=settings.query_max_rows)
        return [_document_from_record(row["document"]) for row in result["rows"]]

    def search(self, request: SearchRequest) -> SearchResponse:
        result = search_documents(request.query, request.top_k)
        return SearchResponse(
            query=request.query,
            results=[
                _search_result_from_record(
                    row["document"],
                    score=float(row.get("score") or 1.0),
                )
                for row in result["rows"]
            ],
        )


def _document_from_record(record: dict[str, object]) -> DocumentSummary:
    properties = _properties(record)
    return DocumentSummary(
        content=str(properties.get("raw_content") or ""),
        source_title=str(properties.get("file_name") or properties.get("id") or "document"),
        file_name=str(properties.get("file_name") or "document"),
        file_type=str(properties.get("source_type") or "txt"),
        location=str(properties.get("id") or ""),
        url=None,
    )


def _search_result_from_record(record: dict[str, object], score: float) -> SearchResult:
    document = _document_from_record(record)
    return SearchResult(
        content=document.content,
        source_title=document.source_title,
        file_name=document.file_name,
        file_type=document.file_type,
        location=document.location,
        url=document.url,
        score=score,
    )


def _properties(record: dict[str, object]) -> dict[str, object]:
    nested = record.get("properties")
    if isinstance(nested, dict):
        return nested
    return record
