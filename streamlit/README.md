# Streamlit

Streamlit 기반 Python 프레임워크 프로젝트입니다.

## Runtime

- Python 3.13
- Streamlit
- Pydantic / pydantic-settings

## Layout

```text
streamlit/
├── src/app.py       # Streamlit entry point
├── src/settings.py  # Streamlit 설정 단일 로딩 지점
├── pyproject.toml
└── uv.lock
```

## Toolchain

이 디렉토리는 `uv`를 사용합니다.

```bash
uv sync
uv run streamlit run src/app.py
```

의존성 추가는 이 디렉토리 안에서 실행합니다.

```bash
uv add <package>
```

## Environment

- 예시 파일: `.env.example`
- 실제 로컬 환경 파일: `.env` (커밋 금지)
- 환경 변수는 `STREAMLIT_` prefix를 사용하며 `src/settings.py`에서 pydantic-settings로 로딩합니다.
