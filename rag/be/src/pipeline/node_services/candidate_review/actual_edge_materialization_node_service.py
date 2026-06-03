# 역할: review graph에서 승인된 RelationshipCandidate를 실제 graph relationship으로 materialize하는 node service이다.
from __future__ import annotations

from query.write import materialize_candidate_edge


class ActualEdgeMaterializationNodeService:
    def materialize(
        self,
        *,
        candidate_id: str,
        reviewer: str,
    ) -> dict[str, object]:
        return materialize_candidate_edge(candidate_id=candidate_id, reviewer=reviewer)
