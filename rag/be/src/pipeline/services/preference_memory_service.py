from __future__ import annotations

from query.write import store_review_note


class PreferenceMemoryService:
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
        return store_review_note(
            candidate_id=candidate_id,
            action=action,
            reviewer=reviewer,
            note=note,
        )
