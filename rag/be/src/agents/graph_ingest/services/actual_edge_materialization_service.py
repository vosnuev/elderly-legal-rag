from __future__ import annotations

from query.service import MemgraphQueryService, get_memgraph_query_service


class ActualEdgeMaterializationService:
    def __init__(self, query_service: MemgraphQueryService | None = None) -> None:
        self._query_service = query_service or get_memgraph_query_service()

    def materialize(
        self,
        *,
        candidate_id: str,
        reviewer: str,
    ) -> dict[str, object]:
        return self._query_service.materialize_edge_candidate(
            candidate_id=candidate_id,
            reviewer=reviewer,
        )
