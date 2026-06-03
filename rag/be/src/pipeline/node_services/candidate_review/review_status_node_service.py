# 역할: review graph에서 reviewer action을 RelationshipCandidate status update로 변환해 저장하는 node service이다.
from __future__ import annotations

from pipeline.schemas import ReviewAction
from query.schema import RelationshipCandidateStatus
from query.write import update_candidate_review_status


class ReviewStatusNodeService:
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
    return RelationshipCandidateStatus.REJECTED
