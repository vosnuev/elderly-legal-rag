from __future__ import annotations

from query.write import materialize_candidate_edge


class ActualEdgeMaterializationService:
    def materialize(
        self,
        *,
        candidate_id: str,
        reviewer: str,
    ) -> dict[str, object]:
        return materialize_candidate_edge(candidate_id=candidate_id, reviewer=reviewer)
