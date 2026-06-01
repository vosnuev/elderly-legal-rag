from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit


def list_materialized_edges_for_candidate(
    candidate_id: str,
    limit: int = 20,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (left)-[edge]->(right)
        WHERE edge.candidate_id = $candidate_id
        RETURN left, edge, right
        LIMIT $limit
        """,
        {
            "candidate_id": candidate_id,
            "limit": bounded_limit(limit),
        },
    )
