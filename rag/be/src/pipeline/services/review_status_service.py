from __future__ import annotations

from pipeline.schemas import ReviewAction
from query.schema import RelationshipCandidateStatus
from query.write import update_candidate_review_status


class ReviewStatusService:
    def apply(
        self,
        *,
        candidate_id: str,
        action: ReviewAction,
        reviewer: str,
    ) -> dict[str, object]:
        return update_candidate_review_status(
            candidate_id=candidate_id,
            status=_to_query_status(action),
            reviewer=reviewer,
        )


def _to_query_status(action: ReviewAction) -> RelationshipCandidateStatus:
    if action is ReviewAction.YES:
        return RelationshipCandidateStatus.APPROVED
    if action is ReviewAction.NO:
        return RelationshipCandidateStatus.REJECTED
    return RelationshipCandidateStatus.RETRY
