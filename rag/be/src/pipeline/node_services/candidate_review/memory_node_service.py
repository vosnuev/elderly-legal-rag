# 역할: review graph에서 ReviewNote provenance를 참고해 자유형 Memory 문서에 entry를 append하는 node service이다.
from __future__ import annotations

from typing import Any

from query.utils import node_properties
from query.write import append_memory_entry


class MemoryNodeService:
    def append_from_review_note(
        self,
        *,
        review_note: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not review_note:
            return {"stored": False}

        note = _review_note_properties(review_note)
        review_note_id = str(note.get("id") or "").strip()
        if not review_note_id:
            return {"stored": False}

        # Memory는 포스트잇 같은 단일 문서다. ReviewNote는 원본 feedback event로만
        # 사용하고, 필요할 때 EVIDENCES_MEMORY link로 provenance를 남긴다.
        return append_memory_entry(
            entry=_memory_entry(note),
            source_review_note_id=review_note_id,
            source_candidate_id=str(note.get("relationship_candidate_id") or "") or None,
        )


def _review_note_properties(review_note: dict[str, Any]) -> dict[str, Any]:
    return node_properties(review_note)


def _memory_entry(note: dict[str, Any]) -> str:
    candidate_id = str(note.get("relationship_candidate_id") or "").strip()
    action = str(note.get("action") or "").strip()
    reviewer = str(note.get("reviewer") or "").strip()
    note_text = str(note.get("note") or "").strip()
    return "\n".join(
        [
            "## Review feedback",
            f"- candidate_id: {candidate_id}",
            f"- action: {action}",
            f"- reviewer: {reviewer}",
            f"- note: {note_text}",
        ]
    )
