from __future__ import annotations

from threading import Lock
from time import time
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.chat import UserProfile
from settings import settings


# 대화 기록 한 턴을 저장하는 모델
class ConversationTurn(BaseModel):
    role: str
    content: str
    created_at: float = Field(default_factory=time)


# 세션별 사용자 정보와 최근 대화 기록 저장하는 모델
class SessionState(BaseModel):
    session_id: str
    user_profile: UserProfile | None = None
    turns: list[ConversationTurn] = Field(default_factory=list)
    updated_at: float = Field(default_factory=time)


# 개발용 메모리 기반 세션 저장소
class InMemorySessionStore:
    # 세션 저장소와 최대 보관 turn 수를 초기화
    def __init__(self, max_turns: int = 12) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = Lock()
        self._max_turns = max_turns

    # TTL이 지난 세션 삭제
    def _cleanup_expired(self) -> None:
        cutoff = time() - settings.session_ttl_seconds
        expired = [sid for sid, s in self._sessions.items() if s.updated_at < cutoff]
        for sid in expired:
            del self._sessions[sid]

    # 기존 세션 ID가 없으면, 새 세션 ID를 발급
    def ensure_session_id(self, session_id: str | None) -> str:
        return session_id or uuid4().hex

    # 세션 상태를 가져오고 없으면, 새로 생성
    def get(self, session_id: str) -> SessionState:
        with self._lock:
            self._cleanup_expired()
            return self._sessions.setdefault(
                session_id,
                SessionState(session_id=session_id),
            )

    # 세션에 사용자 기본 정보 저장
    def save_profile(self, session_id: str, profile: UserProfile) -> None:
        with self._lock:
            self._cleanup_expired()
            state = self._sessions.setdefault(
                session_id,
                SessionState(session_id=session_id),
            )
            state.user_profile = profile
            state.updated_at = time()

    # 세션에 저장된 사용자 기본 정보 삭제
    def clear_profile(self, session_id: str) -> None:
        with self._lock:
            self._cleanup_expired()
            state = self._sessions.setdefault(
                session_id,
                SessionState(session_id=session_id),
            )
            state.user_profile = None
            state.updated_at = time()

    # 세션에 대화 turn을 추가하고, 최근 기록만 유지, 만료 세션 정리
    def add_turn(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            self._cleanup_expired()
            state = self._sessions.setdefault(
                session_id,
                SessionState(session_id=session_id),
            )
            state.turns.append(ConversationTurn(role=role, content=content))
            state.turns = state.turns[-self._max_turns :]
            state.updated_at = time()

    # 특정 세션 메모리 삭제
    def delete(self, session_id: str) -> bool:
        with self._lock:
            self._cleanup_expired()
            return self._sessions.pop(session_id, None) is not None

    # 현재 저장된 세션 수 반환
    def count(self) -> int:
        with self._lock:
            self._cleanup_expired()
            return len(self._sessions)


session_store = InMemorySessionStore()
