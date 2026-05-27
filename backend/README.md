# Backend

메인 백엔드 서비스를 관리하는 Python 프로젝트입니다.

## Runtime

- Python 3.13
- FastAPI
- LangChain
- LangGraph
- Pydantic / pydantic-settings

## Layout

```text
backend/
├── src/app.py       # FastAPI entry point
├── src/settings.py  # backend 설정 단일 로딩 지점
├── pyproject.toml
└── uv.lock
```

## Toolchain

이 디렉토리는 `uv`를 사용합니다.

```bash
uv sync
uv run fastapi dev src/app.py
```

의존성 추가는 이 디렉토리 안에서 실행합니다.

```bash
uv add <package>
```

## Environment

- 예시 파일: `.env.example`
- 실제 로컬 환경 파일: `.env` (커밋 금지)
- 환경 변수는 `BACKEND_` prefix를 사용하며 `src/settings.py`에서 pydantic-settings로 로딩합니다.
- RAG 검색 서버는 기본적으로 `BACKEND_RAG_SEARCH_URL=http://127.0.0.1:8010/search`를 호출합니다.
- 검색 개수와 타임아웃은 `BACKEND_RAG_SEARCH_TOP_K`, `BACKEND_RAG_SEARCH_TIMEOUT_MS`로 조정합니다.
- 채팅 답변에서 RAG 검색을 사용하려면 `rag/` 서비스가 먼저 실행 중이어야 합니다.
