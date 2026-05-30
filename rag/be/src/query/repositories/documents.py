from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.utils import bounded_limit, graph_properties, node_properties
from settings import settings


class DocumentRepository:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def upsert_document_graph(
        self,
        job_id: str,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        document_id = str(document.get("id") or "").strip()
        if not document_id:
            raise ValueError("document.id is required.")

        for chunk in chunks:
            if not str(chunk.get("id") or "").strip():
                raise ValueError("Each chunk requires id.")

        query = """
        MERGE (d:Document {id: $document_id})
        SET d += $document,
            d.last_ingest_job_id = $job_id
        WITH d
        UNWIND $chunks AS chunk
        MERGE (c:Chunk {id: chunk.id})
        SET c += chunk,
            c.document_id = $document_id,
            c.last_ingest_job_id = $job_id
        MERGE (d)-[:HAS_CHUNK]->(c)
        RETURN d.id AS document_id, count(c) AS chunk_count
        """
        return self._client.execute_write(
            query,
            {
                "job_id": job_id,
                "document_id": document_id,
                "document": graph_properties(document),
                "chunks": [graph_properties(chunk) for chunk in chunks],
            },
        )

    def store_document_record(
        self,
        job_id: str,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        document_id = str(document.get("id") or "").strip()
        if not document_id:
            raise ValueError("document.id is required.")

        query = """
        MERGE (d:Document {id: $document_id})
        SET d += $document,
            d.last_ingest_job_id = $job_id
        MERGE (job:IngestJob {id: $job_id})
        SET job.document_id = $document_id,
            job.phase = "uploaded_to_database",
            job.updated_at = localDateTime()
        RETURN d.id AS document_id, job.id AS job_id
        """
        return self._client.execute_write(
            query,
            {
                "job_id": job_id,
                "document_id": document_id,
                "document": graph_properties(document),
            },
        )

    def get_document_record(self, document_id: str) -> dict[str, Any]:
        result = self._client.execute_read(
            """
            MATCH (d:Document {id: $document_id})
            RETURN d AS document
            LIMIT 1
            """,
            {"document_id": document_id},
        )
        if not result["rows"]:
            raise ValueError(f"Document not found: {document_id}")
        return node_properties(result["rows"][0]["document"])

    def get_document_raw_content(self, document_id: str) -> str:
        return str(self.get_document_record(document_id).get("raw_content") or "")

    def list_documents(self, limit: int = 100) -> dict[str, Any]:
        return self._client.execute_read(
            """
            MATCH (d:Document)
            RETURN d AS document
            ORDER BY d.entry_number DESC
            LIMIT $limit
            """,
            {"limit": bounded_limit(limit)},
        )

    def search_documents(self, keyword: str, top_k: int = 20) -> dict[str, Any]:
        query = """
        CALL text_search.search($index_name, $search_query)
        YIELD node, score
        WITH node, score
        WHERE "Document" IN labels(node)
        RETURN node AS document, score
        ORDER BY score DESC
        LIMIT $limit
        """
        return self._client.execute_read(
            query,
            {
                "index_name": settings.document_text_search_index_name,
                "search_query": keyword,
                "limit": bounded_limit(top_k),
            },
        )
