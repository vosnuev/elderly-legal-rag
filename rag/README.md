# RAG

RAG, 문서 파싱, MCP 관련 작업을 관리하는 디렉토리입니다.

## Runtime

- Python 3.13
- Microsoft GraphRAG
- Pydantic / pydantic-settings

GraphRAG 3.x는 Python `>=3.11,<3.14` 범위가 필요하므로 이 디렉토리는 Python 3.13을 기준으로 둡니다.

## Layout

```text
rag/
├── src/app.py       # RAG 작업 진입점
├── src/settings.py  # RAG 설정 단일 로딩 지점
├── pyproject.toml
└── uv.lock
```

## Toolchain

이 디렉토리는 `uv`를 사용합니다.

```bash
uv sync
uv run python src/app.py
```

GraphRAG workspace 초기화가 필요할 때는 이 디렉토리에서 실행합니다.

```bash
uv run graphrag init --root ./workspace --force
```

## Environment

- 예시 파일: `.env.example`
- 실제 로컬 환경 파일: `.env` (커밋 금지)
- 환경 변수는 `RAG_` prefix를 사용하며 `src/settings.py`에서 pydantic-settings로 로딩합니다.
