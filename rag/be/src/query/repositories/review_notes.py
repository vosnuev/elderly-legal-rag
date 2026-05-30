from __future__ import annotations

from typing import Any
from uuid import uuid4

from external.memgraph import MemgraphBoltClient
from query.utils import bounded_limit
from settings import settings


class ReviewNoteRepository:
    def __init__(self, client: MemgraphBoltClient) -> None:
        self._client = client

    def store_review_note(
        self,
        candidate_id: str,
        action: str,
        reviewer: str,
        note: str,
    ) -> dict[str, Any]:
        query = """
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
        """
        return self._client.execute_write(
            query,
            {
                "note_id": str(uuid4()),
                "candidate_id": candidate_id,
                "action": action,
                "reviewer": reviewer,
                "note": note,
            },
        )

    def find_review_notes(self, context: str, limit: int = 10) -> dict[str, Any]:
        query = """
        CALL text_search.search($index_name, $search_query)
        YIELD node, score
        WITH node, score
        WHERE "ReviewNote" IN labels(node)
        RETURN node AS note, score
        ORDER BY score DESC
        LIMIT $limit
        """
        return self._client.execute_read(
            query,
            {
                "index_name": settings.review_note_text_search_index_name,
                "search_query": context,
                "limit": bounded_limit(limit),
            },
        )
