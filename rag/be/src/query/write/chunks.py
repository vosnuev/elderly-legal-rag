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

    # 같은 ingest job에서 agent가 write를 재시도하면 이전 chunk를 교체한다.
    # 이렇게 해야 단일 큰 chunk를 먼저 저장한 뒤 세분화 chunk를 다시 쓰는 경우
    # stale chunk가 downstream shared state나 guard query에 섞이지 않는다.
    result = write_query(
        f"""
        MATCH (d:Document {{id: $document_id}})
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(
            old:Chunk {{document_id: $document_id, last_ingest_job_id: $job_id}}
        )
        WITH d, collect(old) AS old_chunks
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
