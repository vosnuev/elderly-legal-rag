---
name: monorepo-structure
description: Use this skill when adding files, directories, services, or environment examples in the monorepo.
---

# Monorepo Structure Skill

## Top-Level Directories

```txt
frontend/   -> 실제 프론트엔드
backend/    -> 메인 백엔드 서비스
rag/        -> RAG / 문서 파싱 / MCP 관련
streamlit/  -> Streamlit 기반 Python 프레임워크 프로젝트
infra/      -> Podman 등 인프라 실행/관리
docs/       -> 프로젝트 문서
```

## Boundaries

- Keep frontend code in `frontend/`.
- Keep backend service code in `backend/`.
- Keep RAG, parser, document, and MCP-related code in `rag/`.
- Keep Streamlit app/framework work in `streamlit/`.
- Keep container and infrastructure operation files in `infra/`.
- Keep project documentation in `docs/` and update local READMEs as needed.

## Environment Examples

Do not add a root `.env.example` by default.

Place environment examples inside the relevant directory:

- `frontend/.env.example`
- `backend/.env.example`
- `rag/.env.example`
- `streamlit/.env.example`

Real `.env` files are local-only and must not be committed.
