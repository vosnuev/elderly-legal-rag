from __future__ import annotations

from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from settings import settings


# 요청 제한을 초과했을 때 남은 대기 시간 전달
class RateLimitExceeded(RuntimeError):
    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__("요청 횟수 제한을 초과했습니다.")


# 프로세스 메모리에서 클라이언트별 요청 횟수 관리
class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    # 오래된 요청 기록과 빈 key 삭제
    def _cleanup(self, cutoff: float) -> None:
        for key, hits in list(self._hits.items()):
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]

    # 지정한 key가 요청 제한을 넘었는지 검사
    def check(self, key: str) -> None:
        if not settings.rate_limit_enabled:
            return

        now = monotonic()
        window = settings.rate_limit_window_seconds
        cutoff = now - window

        with self._lock:
            self._cleanup(cutoff)
            hits = self._hits.setdefault(key, deque())

            if len(hits) >= settings.rate_limit_requests:
                retry_after = max(window - (now - hits[0]), 1)
                raise RateLimitExceeded(retry_after)

            hits.append(now)


rate_limiter = InMemoryRateLimiter()


# FastAPI 요청에서 클라이언트 주소를 기준으로 rate limit 적용
def enforce_rate_limit(request: Request, scope: str) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{scope}:{client_host}"

    try:
        rate_limiter.check(key)
    except RateLimitExceeded as exc:
        retry_after = str(ceil(exc.retry_after))
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": retry_after},
        ) from exc
