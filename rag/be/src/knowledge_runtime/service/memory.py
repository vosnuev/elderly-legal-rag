"""API-facing service for the shared agent Memory document."""

from __future__ import annotations

from typing import Any

from knowledge_runtime.schemas import (
    MemoryDocumentResponse,
    MemoryDocumentUpdateRequest,
)
from query.read.inspection import list_memory
from query.utils import node_properties
from query.write import update_memory_document


class MemoryService:
    def get_global(self) -> MemoryDocumentResponse:
        result = list_memory(scope="global", status="active", limit=1)
        rows = result.get("rows") or []
        if not rows:
            return MemoryDocumentResponse()

        return _memory_response(node_properties(rows[0]["memory"]))

    def update_global(
        self,
        request: MemoryDocumentUpdateRequest,
    ) -> MemoryDocumentResponse:
        update_memory_document(
            content=request.content,
            scope="global",
            title=request.title,
            update_summary=request.update_summary,
            author=request.author,
        )
        return self.get_global()


def _memory_response(memory: dict[str, Any]) -> MemoryDocumentResponse:
    return MemoryDocumentResponse(
        exists=True,
        id=_optional_str(memory.get("id")),
        scope=str(memory.get("scope") or "global"),
        title=str(memory.get("title") or "Candidate extraction memory"),
        content=str(memory.get("content") or ""),
        version=int(memory.get("version") or 0),
        status=str(memory.get("status") or "active"),
        author=_optional_str(memory.get("author")),
        updated_at=_optional_str(memory.get("updated_at")),
        metadata=memory.get("metadata") if memory.get("metadata") is not None else {},
        evidence_review_note_ids=_string_list(memory.get("evidence_review_note_ids")),
        evidence_candidate_ids=_string_list(
            memory.get("evidence_relationship_candidate_ids"),
        ),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value)
    return normalized or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item)]
