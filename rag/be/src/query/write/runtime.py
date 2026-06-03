from __future__ import annotations

from typing import Any

from query.schema import IngestJobNode, IngestJobPhase
from query.utils import graph_properties
from query.write.core import write_query


def upsert_ingest_job_progress(
    *,
    job_id: str,
    phase: IngestJobPhase | str,
    document_id: str | None,
    chunk_count: int,
    candidate_count: int,
    pending_review_count: int,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    job = IngestJobNode(
        id=job_id,
        job_id=job_id,
        phase=IngestJobPhase.normalize(phase),
        document_id=document_id,
        chunk_count=chunk_count,
        candidate_count=candidate_count,
        pending_review_count=pending_review_count,
        warnings=warnings or [],
        errors=errors or [],
    )
    return write_query(
        """
        MERGE (job:IngestJob {id: $job_id})
        SET job += $progress,
            job.updated_at = localDateTime()
        RETURN job
        """,
        {
            "job_id": job_id,
            "progress": graph_properties(job.model_dump(mode="json")),
        },
    )
