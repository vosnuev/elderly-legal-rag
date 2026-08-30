# 🧭 SKN28-3rd-1Team — 노년 복지·법령 Agentic RAG

<p align="center">
  <b>흩어진 노인·고령층 복지·법령·지역 기관 정보를 자연어로 묻고, 근거와 다음 행동까지 한 번에.</b><br>
  Agentic RAG · GraphRAG · LangGraph · Django Channels · Next.js
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white">
  <img alt="Django Channels" src="https://img.shields.io/badge/Django%20Channels-ASGI-0C4B33?logo=django&logoColor=white">
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-Agent-1C3C3C?logo=langchain&logoColor=white">
  <img alt="OpenRouter" src="https://img.shields.io/badge/OpenRouter-LLM-111827">
  <img alt="Memgraph" src="https://img.shields.io/badge/Memgraph-GraphRAG-FF6B35?logo=memgraph&logoColor=white">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
</p>

## ⌨️ 프로젝트 개요

- **프로젝트명** : SKN28-3rd-1Team — Agentic RAG 기반 노년 복지·법령 상담 서비스
- **기간** : 2026.05.22 ~ 2026.06.25
- **구성원** : 5명 (팀장 · RAG · 프론트엔드 · 백엔드 · 기획·문서)
- **내 역할** : **백엔드 (Django Channels `/chat/stream` · LangGraph Agent · MCP tool 연동)**
- **원본 저장소** : `SKNETWORKS-FAMILY-AICAMP/SKN28-3rd-1Team` (이 저장소는 fork)

---

## ⭐️ 핵심 기능

| 기능 | 입력 | 출력 | 비고 |
|---|---|---|---|
| **자연어 상담** | 사용자 질문 (텍스트/음성) | LLM 답변 + 근거 | 어려운 법령 용어 그대로 OK |
| **스트리밍 답변** | 사용자 질문 | SSE 토큰 스트림 | Next.js `UIMessage` 변환 |
| **근거 문서** | 답변 컨텍스트 | 법령·행정 문서 + 조문 + 원문 일부 | 내부 id 숨김, 사용자 가독 라벨 |
| **기관 정보 UI** | 지역(시/구) | Naver 지도 + 목록 + 상세 | 선택 → 지도 포커스 + 상세 갱신 |
| **음성 입력** | 마이크 | STT 텍스트 → Agent 입력 | 로디 상태 애니메이션 |
| **음성 답변** | 최종 답변 | ElevenLabs TTS stream | Speech Text Agent 정리 |
| **RAG 검색** | 질문 임베딩 | 관련 문서 top-k | MCP tool로 노출 |
| **GraphRAG** | 노드/엣지 쿼리 | Memgraph 관계 검색 | 법령·기관 관계 탐색 |
| **실행 체크리스트** | 답변 + 문서 | 신청 절차 + 다음 행동 | accordion UI |
| **화면 제어** | 답변 + frontend snapshot | typed workspace command 1개 | 한 번에 1 surface만 갱신 |

---

## ⚙️ 시스템 아키텍처

<img src="docs/architecture.png" width="100%">

| 계층 | 서비스 | 역할 | 통신 |
|---|---|---|---|
| **클라이언트** | `frontend_migration/` | Next.js 15 App Router · `/chat` · workspace surface | HTTP · SSE |
| | `/api/chat` (BFF) | backend SSE → AI SDK `UIMessage` 변환 | HTTP |
| **애플리케이션** | `backend/` | Django Channels ASGI · LangGraph Agent 오케스트레이터 | ASGI · SSE |
| | `backend/agents` | Main Agent · Screen Control · Speech Text | LLM |
| | `backend/src/django_backend` | `/health` · `/chat/stream` HTTP/SSE transport | HTTP · SSE |
| | `backend/src/memory` | `session_id` · `InMemorySaver` · TTL 경계 | in-memory |
| **RAG** | `rag/be/` | ingest · 검색 API · MCP endpoint (`/mcp`) | HTTP · MCP |
| | `rag/fe/` | RAG 운영 UI (문서 목록 · ingest job · review queue) | HTTP |
| | `rag/infra/` | Memgraph · Memgraph Lab 실행 설정 | — |
| **외부 MCP** | `external_mcp/` | Naver · Firecrawl · TMAP FastMCP provider tools | MCP |
| **LLM** | OpenRouter · OpenAI · Cerebras | agent별 provider/model · `LLM_AGENT_<AGENT>_*` env | API |
| **관측** | LangSmith | LLM 호출 + tool calling trace | SDK |
| **데이터** | Memgraph (GraphRAG) | 노드·엣지·스키마 | Bolt |
| | Redis | 캐시 · checkpointer 보조 | RESP |
| **인프라** | Docker Compose | `db` / `api` / `weather` / `naver` / `eleven` / `all` profiles | — |
| | AWS | ECR · CodeBuild · CodePipeline · ECS | — |

`/chat/stream` → Main Agent → RAG MCP Tool / External MCP Tool → Memgraph 검색 → 최종 답변 → Screen Control Agent → typed workspace command → frontend 1 surface 갱신.

---

## 🛠️ 기술 스택

### Backend

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Django Channels](https://img.shields.io/badge/Django%20Channels-ASGI-0C4B33?logo=django&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-Settings-E92063?logo=pydantic&logoColor=white)
![uv](https://img.shields.io/badge/uv-Python%20Tooling-6E56CF)

### Agent

![LangChain](https://img.shields.io/badge/LangChain-Agent-1C3C3C?logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Flow-1C3C3C?logo=langchain&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-LLM-111827)
![LangSmith](https://img.shields.io/badge/LangSmith-Tracing-1C3C3C?logo=langchain&logoColor=white)

### RAG

![MCP](https://img.shields.io/badge/MCP-Tool%20Server-111827)
![Memgraph](https://img.shields.io/badge/Memgraph-Graph%20DB-FF6B35?logo=memgraph&logoColor=white)
![GraphRAG](https://img.shields.io/badge/GraphRAG-Search-10B981)

### Frontend

![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-TS-3178C6?logo=typescript&logoColor=white)
![Bun](https://img.shields.io/badge/Bun-Package-000000?logo=bun&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-Style-06B6D4?logo=tailwindcss&logoColor=white)
![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-Components-000000)

### Infra

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Memgraph Lab](https://img.shields.io/badge/Memgraph%20Lab-Graph%20View-FF6B35?logo=memgraph&logoColor=white)
![Make](https://img.shields.io/badge/Make-Workflow-111827)

---

## 👥 팀원

| 이름 | GitHub | 주요 영역 |
|---|---|---|
| 이원빈 | — | 팀장 · 전체 일정 관리 · 작업 방향 컨펌 · 파트별 진행 상황 확인 |
| 김지효 | [@jjeoe0317](https://github.com/jjeoe0317) | RAG · 노인·고령층 관련 법령 데이터 확인 · 문서 전처리 · 임베딩 흐름 |
| 송윤경 | — | 프론트엔드 · 사용자 질문 화면 · API 연결 · 결과 화면 UX · RAG 테스트 케이스 |
| **전하영** | [**@vosnuev**](https://github.com/vosnuev) | **백엔드 · Django Channels `/chat/stream` · LangGraph Agent 실행 구조 · MCP tool 연동** |
| 양도영 | — | 기획·문서 · 서비스 흐름 정리 · README · 발표 자료 · 산출물 |

---

## 📁 저장소 구조

```
SKN28-3rd-1Team/
├── backend/                 # Django Channels + LangGraph Agent 오케스트레이터
│   ├── src/django_backend/  # /health, /chat/stream HTTP/SSE transport
│   ├── src/agents/          # Main Agent · LLM provider · tools
│   ├── src/graph/           # chat turn stream runner
│   ├── src/memory/          # session_id, checkpointer, TTL boundary
│   ├── src/nodes/           # speech/TTS node
│   └── src/agents/*/*.j2    # agent별 prompt
├── rag/
│   ├── be/                  # RAG backend · ingest · 검색 API · MCP endpoint
│   ├── fe/                  # RAG 운영 UI
│   ├── infra/               # Memgraph · Memgraph Lab 실행 설정
│   ├── RAG_ORIGINAL_DATA/   # RAG 대상 원본 JSON 데이터
│   ├── RAG_PREPROCESSED_DATA/ # RAG 입력용 TOON 전처리 데이터
│   ├── related/             # 루트에서 이동한 RAG 관련 실험/작업 공간
│   └── docs/                # RAG 설계 문서
├── external_mcp/            # Naver / Firecrawl / TMAP FastMCP provider tools
├── frontend_migration/      # 현재 active Next.js App Router 상담 UI
│   ├── src/app/             # /chat, /api/chat, /mocks
│   ├── src/page/chat/       # chat controller + BFF stream orchestration
│   ├── src/page/mocks/      # full-size workspace scene fixture
│   ├── src/ui/components/   # chat sidebar · workspace surface · mascot UI
│   └── public/              # mascot sprite · static assets
├── presentation/            # 발표 자료 · 평가 산출물
├── deploy/                  # 통합 배포 (Docker · AWS · Makefile)
├── docs/                    # 회의록 · 온보딩 · 에이전트 가이드라인
└── AGENTS.md                # 협업 및 agent 작업 규칙
```

---

## 🚀 빠른 시작

> 환경변수는 **Infisical + Varlock**로 관리한다. 실제 `.env`는 커밋 금지, schema(`*.env.schema`)가 계약 기준.

### 통합 (Make)

```bash
cd deploy/makefile
make dev              # frontend_migration + backend 병렬 실행
make compose-up       # 전체 스택 (frontend · backend · RAG · Memgraph · Redis)
```

기본 접속:

| 서비스 | URL |
|---|---|
| Frontend (Migration) | http://127.0.0.1:3005 |
| Frontend `/chat` | http://127.0.0.1:3005/chat |
| Backend API | http://127.0.0.1:8000 |
| Memgraph Lab | http://127.0.0.1:3000 |
| Memgraph Bolt | bolt://127.0.0.1:7687 |

### 개별 실행

```bash
cd frontend_migration && make start    # Next.js /chat
cd backend && make start                # Django Channels
cd rag && make infra-up                 # Memgraph + Lab
cd rag && make be-start                 # RAG backend + MCP
cd external_mcp && make start           # Naver/Firecrawl/TMAP MCP
```

### 채팅 API 테스트

```bash
curl -N http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"readme-test-1","message":"안녕. 너는 어떤 일을 할 수 있어?"}'
```

---

## 🔐 환경 변수

| 서비스 | Schema | 주요 값 |
|---|---|---|
| Shared | `.env.schema` | `APP_ENV` |
| Frontend Migration | `frontend_migration/.env.schema` | BFF backend URL · Naver map public key · TTS BFF key |
| Backend | `backend/.env.schema` | LLM provider API key · CORS · RAG MCP URL |
| External MCP | `external_mcp/.env.schema` | Naver / Firecrawl / TMAP API key · endpoint |
| RAG Backend | `rag/be/.env.schema` | Memgraph 연결 · MCP endpoint |
| RAG Frontend | `rag/fe/.env.schema` | RAG API base URL |
| RAG Infra | `rag/infra/.env.schema` | Memgraph/Lab 포트 |
| Deploy | `deploy/docker/.env.schema` | 통합 Docker Compose host 포트 · public build args |

- `make env-check`로 Infisical 주입 + Varlock schema 계약 검증
- env var / Infisical / Varlock / LLM 이름 변경 시 `AGENTS.md`의 `env-var-governance` skill과 `docs/legacy/llm_env_naming_convention.md` 먼저 확인

---

## 📚 문서

| 문서 | 내용 |
|---|---|
| [`AGENTS.md`](AGENTS.md) | 협업 및 agent 작업 규칙 |
| [`frontend_migration/README.md`](frontend_migration/README.md) | 현재 active Next.js `/chat` · `/api/chat` · workspace · env |
| [`backend/README.md`](backend/README.md) | Backend Agent 구조 · `/chat/stream` SSE · MCP 연결 |
| [`rag/README.md`](rag/README.md) | RAG 서브시스템 전체 구조 |
| [`rag/be/README.md`](rag/be/README.md) | RAG Backend API · MCP endpoint · 환경 변수 |
| [`rag/fe/README.md`](rag/fe/README.md) | RAG 운영 UI 실행 |
| [`external_mcp/README.md`](external_mcp/README.md) | Naver · Firecrawl · TMAP MCP tool 서버 |
| [`deploy/README.md`](deploy/README.md) | local dev · Docker Compose · AWS 배포 준비 |
| [`docs/chat_workspace_surfaces.md`](docs/chat_workspace_surfaces.md) | workspace surface 스키마 |
| [`docs/requirement_list_ops.md`](docs/requirement_list_ops.md) | 운영 요건 정리 |
| [`docs/legacy/llm_env_naming_convention.md`](docs/legacy/llm_env_naming_convention.md) | LLM agent/provider/model env naming · Infisical 동기화 |

### 제출 산출물

| 필수 산출물 | 제출 위치 |
|---|---|
| 요구사항·화면정의서 | [`presentation/ppt/reviewable-graphrag-service-presentation-v4.pptx`](presentation/ppt/reviewable-graphrag-service-presentation-v4.pptx) |
| 개발된 LLM 연동 웹앱 | [배포 Application](https://d2psjdqzzwvjpi.cloudfront.net/) |
| 시스템 구성도 | [Eraser 시스템 구성도](https://app.eraser.io/workspace/QaaF195Z5KgdFDGK7GiV) |
| 테스트 계획·결과 보고서 | [`presentation/test_results/unit_test.pdf`](presentation/test_results/unit_test.pdf), [`presentation/test_results/integration_test.pdf`](presentation/test_results/integration_test.pdf) |
| 발표 PDF | [`presentation/ppt/옆집 손주_찐최종 (1).pdf`](presentation/ppt/옆집%20손주_찐최종%20(1).pdf) |
| 발표 스크립트 | [`presentation/ppt/20min-presentation-script-v4.md`](presentation/ppt/20min-presentation-script-v4.md) |

---

<p align="center">
  <sub>SK네트웍스 Family AI 캠프 28기 · 3차 프로젝트 1팀 · SKN28-3rd-1Team</sub>
</p>
