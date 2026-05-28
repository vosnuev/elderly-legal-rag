from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendChatResult:
    error: str | None
    response: dict[str, object] | None
