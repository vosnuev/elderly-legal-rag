from __future__ import annotations

from threading import Lock
from time import time
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.chat import UserProfile


class ConversationTurn(BaseModel):
    role: str
    content: str
    created_at: float = Field(default_factory=time)


class SessionState(BaseModel):
    session_id: str
    user_profile: UserProfile | None = None
    turns: list[ConversationTurn] = Field(default_factory=list)
    updated_at: float = Field(default_factory=time)


class InMemorySessionStore:
    def __init__(self, max_turns: int = 12) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = Lock()
        self._max_turns = max_turns

    def ensure_session_id(self, session_id: str | None) -> str:
        return session_id or uuid4().hex

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            return self._sessions.setdefault(
                session_id,
                SessionState(session_id=session_id),
            )

    def save_profile(self, session_id: str, profile: UserProfile) -> None:
        with self._lock:
            state = self._sessions.setdefault(
                session_id,
                SessionState(session_id=session_id),
            )
            state.user_profile = profile
            state.updated_at = time()

    def add_turn(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            state = self._sessions.setdefault(
                session_id,
                SessionState(session_id=session_id),
            )
            state.turns.append(ConversationTurn(role=role, content=content))
            state.turns = state.turns[-self._max_turns :]
            state.updated_at = time()

session_store = InMemorySessionStore()
