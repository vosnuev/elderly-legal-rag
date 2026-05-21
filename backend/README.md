# Backend

메인 백엔드 서비스를 관리하는 Python 프로젝트입니다.

## Toolchain

이 디렉토리는 `uv`를 사용합니다.

```bash
uv sync
uv run python main.py
```

의존성 추가는 이 디렉토리 안에서 실행합니다.

```bash
uv add <package>
```

## Environment

- 예시 파일: `.env.example`
- 실제 로컬 환경 파일: `.env` (커밋 금지)
