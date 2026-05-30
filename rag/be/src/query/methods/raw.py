from __future__ import annotations

from typing import Any

from external.memgraph import MemgraphBoltClient
from query.guard import validate_read_query, validate_write_query
from query.utils import bounded_limit


class RawCypherQueryMethods:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def read_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        limit = bounded_limit(max_rows)
        validated = validate_read_query(query, max_rows=limit)
        result = self._client.execute_read(validated.query, parameters)
        result["warnings"] = list(validated.warnings)
        result["access"] = validated.access
        return result

    def write_query(
        self,
        query: str,
        job_id: str,
        purpose: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        validated = validate_write_query(query, job_id=job_id, purpose=purpose)
        result = self._client.execute_write(validated.query, parameters)
        result["access"] = validated.access
        result["job_id"] = job_id
        result["purpose"] = purpose
        return result
