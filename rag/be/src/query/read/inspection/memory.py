from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit


def list_agent_memory(
    scope: str | None = None,
    memory_kind: str | None = None,
    status: str | None = "active",
    limit: int = 100,
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (memory:AgentMemory)
        WHERE ($scope IS NULL OR memory.scope = $scope)
          AND ($memory_kind IS NULL OR memory.memory_kind = $memory_kind)
          AND ($status IS NULL OR memory.status = $status)
        RETURN memory
        ORDER BY memory.version DESC, memory.id DESC
        LIMIT $limit
        """,
        {
            "scope": scope,
            "memory_kind": memory_kind,
            "status": status,
            "limit": bounded_limit(limit),
        },
    )
