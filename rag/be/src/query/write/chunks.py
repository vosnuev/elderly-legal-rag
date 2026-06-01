from __future__ import annotations

from typing import Any
from uuid import uuid4

from query.schema import ChunkNode
from query.utils import graph_properties
from query.write.core import write_query


def write_chunks_for_document(
    *,
    document_id: str,
    chunks: list[ChunkNode | dict[str, Any]],
    job_id: str = "",
) -> dict[str, Any]:
    records = [
        _chunk_record(document_id=document_id, chunk=chunk)
        for chunk in chunks
    ]
    if not records:
        return {"stored_count": 0, "chunk_ids": []}

    result = write_query(
        """
        MATCH (d:Document {id: $document_id})
        UNWIND $chunks AS chunk
        MERGE (c:Chunk {id: chunk.id})
        ON CREATE SET c.created_at = localDateTime()
        SET c += chunk,
            c.document_id = $document_id,
            c.last_ingest_job_id = $job_id
        MERGE (d)-[:HAS_CHUNK]->(c)
        RETURN count(c) AS stored_count,
               collect(c.id) AS chunk_ids
        """,
        {
            "job_id": job_id,
            "document_id": document_id,
            "chunks": [graph_properties(record) for record in records],
        },
    )
    _require_expected_write_count(result, len(records), "Chunk")
    return result


def _chunk_record(
    *,
    document_id: str,
    chunk: ChunkNode | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(chunk, ChunkNode):
        source = chunk.model_dump()
    else:
        source = dict(chunk)
    source.setdefault("id", str(uuid4()))
    source["document_id"] = document_id
    source.setdefault("embedding_status", "pending")
    return ChunkNode.model_validate(source).model_dump()


def _require_expected_write_count(
    result: dict[str, Any],
    expected_count: int,
    label: str,
) -> None:
    if not result.get("rows"):
        raise ValueError(f"{label} write returned no rows.")
    stored_count = int(result["rows"][0].get("stored_count") or 0)
    if stored_count != expected_count:
        raise ValueError(
            f"{label} write stored {stored_count} rows; expected {expected_count}."
        )
