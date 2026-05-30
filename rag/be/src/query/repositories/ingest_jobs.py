from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.utils import graph_properties


class IngestJobRepository:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def store_ingest_progress(self, progress: dict[str, Any]) -> dict[str, Any]:
        job_id = str(progress.get("job_id") or "").strip()
        if not job_id:
            return {"stored": False}
        query = """
        MERGE (job:IngestJob {id: $job_id})
        SET job += $progress,
            job.updated_at = localDateTime()
        RETURN job
        """
        return self._client.execute_write(
            query,
            {"job_id": job_id, "progress": graph_properties(progress)},
        )

    def get_ingest_progress(self, job_id: str) -> dict[str, Any]:
        return self._client.execute_read(
            """
            MATCH (job:IngestJob {id: $job_id})
            RETURN job
            LIMIT 1
            """,
            {"job_id": job_id},
        )
