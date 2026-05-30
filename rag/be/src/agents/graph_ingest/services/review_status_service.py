from __future__ import annotations

from agents.graph_ingest.schemas import ReviewAction
from query.service import MemgraphQueryService, get_memgraph_query_service


class ReviewStatusService:
    def __init__(self, query_service: MemgraphQueryService | None = None) -> None:
        self._query_service = query_service or get_memgraph_query_service()

    def apply(
        self,
        *,
        candidate_id: str,
        action: ReviewAction,
        reviewer: str,
    ) -> dict[str, object]:
        return self._query_service.review_edge_candidate(
            candidate_id=candidate_id,
            action=_to_query_action(action),
            reviewer=reviewer,
        )


def _to_query_action(action: ReviewAction) -> str:
    if action is ReviewAction.YES:
        return "approve"
    if action is ReviewAction.NO:
        return "reject"
    return "retry"
