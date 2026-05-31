from __future__ import annotations

from uuid import uuid4

from query.write import write_query


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
        return write_query(
            """
            MATCH (candidate:RelationshipCandidate {id: $candidate_id})
            CREATE (note:ReviewNote {
                id: $note_id,
                candidate_id: $candidate_id,
                action: $action,
                reviewer: $reviewer,
                note: $note,
                created_at: localDateTime()
            })
            MERGE (candidate)-[:HAS_REVIEW_NOTE]->(note)
            RETURN note
            """,
            {
                "note_id": str(uuid4()),
                "candidate_id": candidate_id,
                "action": action,
                "reviewer": reviewer,
                "note": note.strip(),
            },
        )
