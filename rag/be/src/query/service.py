from __future__ import annotations

from functools import lru_cache
from typing import Any

from external.memgraph import MemgraphBoltClient, get_memgraph_bolt_client
from query.methods import (
    GraphTraversalQueryMethods,
    RawCypherQueryMethods,
    SchemaQueryMethods,
    TextSearchQueryMethods,
    VectorSearchQueryMethods,
)
from query.repositories import (
    ChunkRepository,
    DocumentRepository,
    IngestJobRepository,
    RelationshipCandidateRepository,
    ReviewNoteRepository,
)


class MemgraphQueryService:
    """Facade for Memgraph query methods and graph-schema repositories."""

    def __init__(self, client: MemgraphBoltClient | None = None) -> None:
        self._client = client or get_memgraph_bolt_client()
        self._raw = RawCypherQueryMethods(self._client)
        self._schema = SchemaQueryMethods(self._client)
        self._text_search = TextSearchQueryMethods(self._client)
        self._vector_search = VectorSearchQueryMethods(self._client)
        self._traversal = GraphTraversalQueryMethods(self._client)
        self._documents = DocumentRepository(self._client)
        self._chunks = ChunkRepository(self._client)
        self._candidates = RelationshipCandidateRepository(self._client)
        self._review_notes = ReviewNoteRepository(self._client)
        self._ingest_jobs = IngestJobRepository(self._client)

    def read_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        return self._raw.read_query(query, parameters, max_rows)

    def write_query(
        self,
        query: str,
        job_id: str,
        purpose: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._raw.write_query(query, job_id, purpose, parameters)

    def schema_read(self) -> dict[str, Any]:
        return self._schema.schema_read()

    def text_search(
        self,
        keyword: str,
        top_k: int = 20,
        index_name: str | None = None,
    ) -> dict[str, Any]:
        return self._text_search.text_search(keyword, top_k, index_name)

    def keyword_search(self, keyword: str, top_k: int = 20) -> dict[str, Any]:
        return self._text_search.keyword_search(keyword, top_k)

    def vector_search(
        self,
        index_name: str,
        embedding: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        return self._vector_search.vector_search(index_name, embedding, top_k)

    def graph_traverse(
        self,
        node_id: str,
        id_property: str = "id",
        max_depth: int = 2,
        max_rows: int = 50,
    ) -> dict[str, Any]:
        return self._traversal.graph_traverse(
            node_id,
            id_property,
            max_depth,
            max_rows,
        )

    def probe_existing_context(
        self,
        keyword: str,
        top_k: int = 20,
    ) -> dict[str, Any]:
        return {
            "text_matches": self.text_search(keyword, top_k),
            "schema": self.schema_read(),
        }

    def upsert_document_graph(
        self,
        job_id: str,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._documents.upsert_document_graph(job_id, document, chunks)

    def store_document_record(
        self,
        job_id: str,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        return self._documents.store_document_record(job_id, document)

    def get_document_record(self, document_id: str) -> dict[str, Any]:
        return self._documents.get_document_record(document_id)

    def get_document_raw_content(self, document_id: str) -> str:
        return self._documents.get_document_raw_content(document_id)

    def list_documents(self, limit: int = 100) -> dict[str, Any]:
        return self._documents.list_documents(limit)

    def search_documents(self, keyword: str, top_k: int = 20) -> dict[str, Any]:
        return self._documents.search_documents(keyword, top_k)

    def store_chunks(
        self,
        job_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._chunks.store_chunks(job_id, document_id, chunks)

    def store_chunk_embeddings(
        self,
        job_id: str,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._chunks.store_chunk_embeddings(job_id, chunks)

    def store_edge_candidates(
        self,
        job_id: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._candidates.store_edge_candidates(job_id, candidates)

    def review_edge_candidate(
        self,
        candidate_id: str,
        action: str,
        reviewer: str = "system",
    ) -> dict[str, Any]:
        return self._candidates.review_edge_candidate(candidate_id, action, reviewer)

    def get_edge_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self._candidates.get_edge_candidate(candidate_id)

    def materialize_edge_candidate(
        self,
        candidate_id: str,
        reviewer: str,
    ) -> dict[str, Any]:
        return self._candidates.materialize_edge_candidate(candidate_id, reviewer)

    def store_review_note(
        self,
        candidate_id: str,
        action: str,
        reviewer: str,
        note: str,
    ) -> dict[str, Any]:
        return self._review_notes.store_review_note(
            candidate_id,
            action,
            reviewer,
            note,
        )

    def find_review_notes(self, context: str, limit: int = 10) -> dict[str, Any]:
        return self._review_notes.find_review_notes(context, limit)

    def store_ingest_progress(self, progress: dict[str, Any]) -> dict[str, Any]:
        return self._ingest_jobs.store_ingest_progress(progress)

    def get_ingest_progress(self, job_id: str) -> dict[str, Any]:
        return self._ingest_jobs.get_ingest_progress(job_id)

    def list_pending_edge_candidates(self, limit: int = 50) -> dict[str, Any]:
        return self._candidates.list_pending_edge_candidates(limit)


@lru_cache
def get_memgraph_query_service() -> MemgraphQueryService:
    return MemgraphQueryService()
