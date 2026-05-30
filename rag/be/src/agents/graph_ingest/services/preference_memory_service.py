from __future__ import annotations

from query.service import MemgraphQueryService, get_memgraph_query_service


class PreferenceMemoryService:
    def __init__(self, query_service: MemgraphQueryService | None = None) -> None:
        self._query_service = query_service or get_memgraph_query_service()

    def store_note(
        self,
        *,
        candidate_id: str,
        action: str,
        reviewer: str,
        note: str | None,
    ) -> dict[str, object]:
        if not note or not note.strip():
            return {"stored": False}
        return self._query_service.store_review_note(
            candidate_id=candidate_id,
            action=action,
            reviewer=reviewer,
            note=note.strip(),
        )
