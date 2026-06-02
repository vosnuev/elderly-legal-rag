"""Document catalog query service."""

from __future__ import annotations

from knowledge_runtime.documents.catalog import DocumentCatalog
from knowledge_runtime.schemas import DocumentSummary, SearchRequest, SearchResponse


class CatalogService:
    def __init__(self, *, catalog: DocumentCatalog) -> None:
        self._catalog = catalog

    def list_documents(self) -> list[DocumentSummary]:
        return self._catalog.list_documents()

    def search(self, request: SearchRequest) -> SearchResponse:
        return self._catalog.search(request)
