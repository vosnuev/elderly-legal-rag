from __future__ import annotations

from pipeline.schemas import ReviewAction
from query.write import write_query


class ReviewStatusService:
    def apply(
        self,
        *,
        candidate_id: str,
        action: ReviewAction,
        reviewer: str,
    ) -> dict[str, object]:
        return write_query(
            """
            MATCH (candidate:RelationshipCandidate {id: $candidate_id})
            SET candidate.status = $status,
                candidate.reviewed_by = $reviewer,
                candidate.reviewed_at = localDateTime()
            RETURN candidate
            """,
            {
                "candidate_id": candidate_id,
                "status": _to_query_status(action),
                "reviewer": reviewer,
            },
        )


def _to_query_status(action: ReviewAction) -> str:
    if action is ReviewAction.YES:
        return "approved"
    if action is ReviewAction.NO:
        return "rejected"
    return "retry"
