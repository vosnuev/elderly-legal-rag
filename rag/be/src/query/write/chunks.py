from __future__ import annotations

from typing import Any

from query.schema import ChunkNode
from query.utils import db_generated_id_expression, graph_properties
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
    chunk_indexes = [
        int(record["chunk_index"])
        for record in records
        if "chunk_index" in record
    ]
    replace_existing = 1 in chunk_indexes

    # chunking_agent는 긴 문서에서 write_chunk_tool을 여러 번 호출할 수 있다.
    # 첫 batch(chunk_index=1)는 같은 job의 기존 chunk를 모두 reset하고, 이후
    # batch는 같은 chunk_index만 교체한다. 이렇게 하면 작은 batch append와
    # batch-level retry를 모두 허용하면서 stale duplicate index를 막을 수 있다.
    result = write_query(
        f"""
        MATCH (d:Document {{id: $document_id}})
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(
            old:Chunk {{document_id: $document_id, last_ingest_job_id: $job_id}}
        )
        WITH d, collect(old) AS candidate_old_chunks
        WITH d,
             [
               old IN candidate_old_chunks
               WHERE old IS NOT NULL
                 AND ($replace_existing OR old.chunk_index IN $chunk_indexes)
             ] AS old_chunks
        FOREACH (old IN old_chunks | DETACH DELETE old)
        WITH d
        UNWIND $chunks AS chunk
        CREATE (c:Chunk)
        SET c += chunk,
            c.id = {db_generated_id_expression()},
            c.document_id = $document_id,
            c.last_ingest_job_id = $job_id,
            c.created_at = localDateTime(),
            c.updated_at = localDateTime()
        MERGE (d)-[:HAS_CHUNK]->(c)
        RETURN count(c) AS stored_count,
               collect(c.id) AS chunk_ids
        """,
        {
            "job_id": job_id,
            "document_id": document_id,
            "chunk_indexes": chunk_indexes,
            "replace_existing": replace_existing,
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
        source = chunk.model_dump(exclude_none=True)
    else:
        source = dict(chunk)
    source["document_id"] = document_id
    source.setdefault("embedding_status", "pending")
    record = ChunkNode.model_validate(source).model_dump(exclude_none=True)
    record.pop("id", None)
    return record


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
