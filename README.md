# 옆집 손주 — 노인·고령층 법률 상담 서비스 (GraphRAG + Agentic RAG)

> An Agentic RAG + GraphRAG-based legal consultation service for the elderly, built on public legal documents and statutes. / 노인·고령층 관련 법령과 공공 문서를 근거로 자연어 질문에 답변하는 상담 서비스

**SK Networks AI Camp 28기 3차 프로젝트 — 1팀**

---

## 🛠️ Tech Stack (기술 스택)

### Backend & Agent (백엔드 · 에이전트)

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.3-1C3C3C?logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?logo=langchain&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-LLM%20Gateway-111827)
![LangSmith](https://img.shields.io/badge/LangSmith-Tracing-1C3C3C?logo=langchain&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2-E92063?logo=pydantic&logoColor=white)
![uv](https://img.shields.io/badge/uv-Package%20Manager-6E56CF)

### RAG (검색 증강 생성)

![Memgraph](https://img.shields.io/badge/Memgraph-GraphRAG-FF6B35)
![Neo4j](https://img.shields.io/badge/Neo4j-Compatible-4581C3?logo=neo4j&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-Tool%20Server-111827)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![GraphRAG](https://img.shields.io/badge/GraphRAG-3.0-10B981)
![Firecrawl](https://img.shields.io/badge/Firecrawl-Web%20Crawl-F97316)

### Frontend (프론트엔드)

![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-Build-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-Style-06B6D4?logo=tailwindcss&logoColor=white)
![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-Components-000000)
![Streamlit](https://img.shields.io/badge/Streamlit-Prototype-FF4B4B?logo=streamlit&logoColor=white)

### Infra (인프라)

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Docs-222222?logo=githubpages&logoColor=white)

---

## ✨ Features (주요 기능)

| 기능 | 설명 |
|---|---|
| 자연어 법률 상담 | 법률 용어 없이 구어체로 질문하면 이해하기 쉬운 답변 제공 |
| 근거 문서 함께 제공 | 노인복지법·기초연금법·고령자고용법 등 실제 법령과 출처 함께 표시 |
| Agentic RAG | LangGraph Main Agent가 질문을 판단해 필요한 경우 RAG MCP Tool 호출 |
| GraphRAG 관계 검색 | Memgraph 기반 그래프 DB로 조문 간 관계 추적 및 연관 법령 탐색 |
| 상담형 UI | Streamlit 프로토타입 + React 프론트엔드 두 가지 인터페이스 제공 |
| RAG 운영 UI | 문서 ingest, 검색 결과 review, edge candidate 확인용 관리 화면 |
| LangSmith 추적 | LLM 호출·tool calling 전 과정 trace 기록 |
| Docker 통합 실행 | 전체 서비스를 단일 `docker compose up`으로 구동 |

---

## 📁 Project Structure (프로젝트 구조)

```
SKN28-3rd-1Team/
├── backend/                    # FastAPI + LangGraph Agent Orchestrator
│   ├── src/
│   │   ├── app.py              # FastAPI 앱 생성 및 라우터 등록
│   │   ├── settings.py         # Pydantic-settings 환경 변수 관리
│   │   ├── api/                # /chat, /health API 라우터
│   │   ├── agent/              # LangGraph Agent, OpenRouter LLM, MCP Tool 연결
│   │   └── prompt/             # Agent 시스템 프롬프트
│   ├── Dockerfile
│   └── pyproject.toml          # Python 3.13, FastAPI, LangChain, LangGraph 의존성
│
├── rag/                        # RAG 서브시스템 전체
│   ├── be/                     # RAG Backend (FastAPI + Memgraph + Redis + MCP)
│   │   ├── src/                # ingest, search, MCP endpoint 구현
│   │   └── pyproject.toml      # graphrag, neo4j, redis, mcp 의존성
│   ├── fe/                     # RAG 운영 UI (React + Vite + Tailwind)
│   ├── infra/                  # Memgraph + Memgraph Lab Docker Compose
│   ├── RAG_ORIGINAL_DATA/      # 법령 원본 JSON 데이터
│   ├── RAG_PREPROCESSED_DATA/  # 전처리된 TOON 형식 데이터
│   └── docs/                   # RAG 설계 문서
│
├── streamlit/                  # 상담형 UI 프로토타입 (Python + Streamlit)
│   ├── streamlit.py            # 앱 진입점
│   └── src/                    # 화면 구성, backend API 연결 로직
│
├── frontend/                   # 최종 React 프론트엔드 (React 19 + TypeScript)
│
├── infra/                      # 통합 Docker Compose (전체 서비스 통합 실행)
│   └── docker-compose.yml      # backend, rag-be, rag-fe, streamlit, memgraph, redis
│
├── docs_web/                   # GitHub Pages 프로젝트 소개 문서 웹
├── docs/                       # 회의록, 온보딩, 개발 가이드
├── presentation/               # 발표 자료, 테스트 데이터, 평가 산출물
│   ├── ppt/                    # 발표 PDF/PPTX, 스크립트, Memgraph Lab 시연 캡처
│   └── test-data/              # benchmark, LLM-as-a-judge 결과
├── rag-red-team/               # Neo4j 기반 GraphRAG 실험 공간
├── AGENTS.md                   # AI Agent 협업 규칙 및 Git 워크플로
└── README.md
```

---

## 🔄 Usage Flow (사용 흐름)

```
사용자 질문 입력
  ↓
[Frontend / Streamlit]  — 질문 화면, 답변 표시
  ↓  HTTP POST /chat
[Backend — FastAPI]     — 요청 수신 및 Agent 실행
  ↓
[LangGraph Main Agent]  — 질문 분류 및 흐름 판단
  ↓  MCP Tool 호출
[RAG MCP Tool Server]   — 문서 검색 요청 수신
  ↓  Cypher 쿼리
[Memgraph GraphDB]      — 법령 그래프 검색, 관계 탐색
  ↓  검색 결과 반환
[OpenRouter LLM]        — 근거 문서 기반 답변 생성
  ↓
[사용자 화면]           — 답변 + 출처 표시
```

### 서비스별 역할

| 서비스 | 역할 |
|---|---|
| Frontend / Streamlit | 사용자 질문 입력 및 답변 표시 |
| Backend (FastAPI) | `/chat` API 수신, LangGraph Agent 실행 |
| RAG Backend | 문서 ingest, 검색 API, MCP endpoint 제공 |
| Memgraph | GraphRAG용 법령 그래프 데이터 저장 |
| Redis | RAG job queue 및 캐시 |
| Memgraph Lab | 그래프 시각화 및 Cypher 쿼리 실행 |

---

## 🏗️ Architecture (아키텍처)

```
                     ┌──────────────────────┐
                     │  Frontend / Streamlit │
                     └──────────┬───────────┘
                                │ HTTP POST /chat
                     ┌──────────▼───────────┐
                     │   Backend (FastAPI)   │
                     │  LangGraph Main Agent │
                     └──────────┬───────────┘
                                │ MCP Tool Call
                     ┌──────────▼───────────┐
                     │  RAG Backend (FastAPI)│
                     │  MCP endpoint /mcp/  │
                     └────┬──────────┬──────┘
                          │          │
              ┌───────────▼──┐  ┌────▼──────┐
              │  Memgraph    │  │  Redis    │
              │  (GraphDB)   │  │  (Cache)  │
              └──────────────┘  └───────────┘
```

### 아키텍처 원칙

| 원칙 | 설명 |
|---|---|
| 영역 분리 | Frontend, Backend, RAG를 독립 서비스로 분리 |
| Main Agent 중심 | Backend Agent가 질문 판단 및 답변 흐름 조율 |
| MCP Tool 호출 | Agent는 RAG 내부 구현을 몰라도 MCP Tool로 검색 기능 사용 |
| GraphRAG 확장 | Memgraph 기반 관계 검색으로 벡터 검색 한계 보완 |
| 컨테이너 기반 실행 | 전체 서비스를 Docker Compose 단일 명령으로 실행 |

---

## ⚙️ Environment Setup (환경 설정)

각 서비스 디렉터리의 `.env.example`을 복사해 실제 값을 채웁니다. 실제 `.env` 파일은 Git에 커밋하지 않습니다.

| 서비스 | 예시 파일 | 주요 환경 변수 |
|---|---|---|
| Backend | `backend/.env.example` | `OPENROUTER_API_KEY`, `LANGSMITH_API_KEY`, `BACKEND_RAG_MCP_URL` |
| Streamlit | `streamlit/.env.example` | `STREAMLIT_BACKEND_BASE_URL`, `STREAMLIT_CHAT_BACKEND_MOCK` |
| RAG Backend | `rag/be/.env.example` | `RAG_MEMGRAPH_URI`, `RAG_REDIS_URL`, `OPENAI_API_KEY` |
| RAG Frontend | `rag/fe/.env.example` | `VITE_RAG_API_BASE_URL` |
| Infra | `infra/.env.example` | 포트 매핑, 컨테이너 이름 |

---

## 🚀 How to Run (실행 방법)

### 1) 통합 Docker Compose 실행 (권장)

Backend, Streamlit, RAG Backend, RAG Frontend, Memgraph, Memgraph Lab, Redis를 한 번에 실행합니다.

```bash
# 환경 변수 파일 준비
cp infra/.env.example infra/.env
cp backend/.env.example infra/.env_backend
cp streamlit/.env.example infra/.env_streamlit
cp rag/be/.env.example infra/.env_rag_be
cp rag/fe/.env.example infra/.env_rag_fe
cp rag/infra/.env.example infra/.env_rag_infra

# 전체 서비스 실행
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build
```

기본 접속 주소:

| 서비스 | 주소 |
|---|---|
| Backend API | http://127.0.0.1:8100 |
| Streamlit UI | http://127.0.0.1:8501 |
| RAG Backend | http://127.0.0.1:8110 |
| RAG Frontend | http://127.0.0.1:5174 |
| Memgraph Lab | http://127.0.0.1:3000 |
| Memgraph Bolt | bolt://127.0.0.1:7687 |
| Redis | redis://127.0.0.1:6379/0 |

### 2) Backend 단독 실행

```bash
cd backend
cp .env.example .env   # OPENROUTER_API_KEY 등 값 입력
uv sync

# 환경 변수 로드 후 서버 시작
set -a && source .env && set +a
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

상태 확인:

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

채팅 API 테스트:

```bash
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-1","message":"기초연금 신청 방법을 알려줘"}' \
  | python -m json.tool
```

### 3) Streamlit UI 단독 실행

```bash
cd streamlit
cp .env.example .env   # STREAMLIT_BACKEND_BASE_URL=http://127.0.0.1:8000 설정
uv sync
uv run streamlit run streamlit.py
```

### 4) RAG Backend 단독 실행

```bash
cd rag/be
cp .env.example .env
uv sync
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8010
```

주요 엔드포인트:

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | /health | 상태 확인 |
| POST | /ingest | 문서 ingestion |
| POST | /search | 문서 검색 |
| GET | /api/documents | 문서 목록 |
| POST | /api/documents/search | 문서 검색 |
| GET | /api/review/edge-candidates | 그래프 edge 후보 조회 |
| — | /mcp | MCP Tool Server endpoint |

### 5) RAG Infra (Memgraph + Redis) 단독 실행

```bash
cd rag
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

### 6) RAG Frontend (운영 UI) 실행

```bash
cd rag/fe
bun install
bun run dev
# → http://127.0.0.1:5173
```

### 7) 검증 (Validation)

```bash
# Backend 테스트
cd backend
PYTHONPATH=src uv run python -m compileall src scripts tests
PYTHONPATH=src uv run python -m unittest discover -s tests

# RAG Backend 테스트
cd rag/be
PYTHONPATH=src uv run python -m compileall src tests
PYTHONPATH=src uv run python -m unittest discover -s tests
```

---

## 👥 Team (팀원)

SK Networks AI Camp 28기 3차 프로젝트 1팀 (2026년 5월–6월)

| 이름 | 역할 |
|---|---|
| 이원빈 | 팀장 — 전체 일정 관리, 작업 방향 컨펌 |
| 김지효 | RAG — 법령 데이터 수집, 문서 전처리, 임베딩 흐름 |
| 송윤경 | Frontend — 사용자 화면 구성, API 연결, UX 설계 |
| 전하영 | Backend — FastAPI /chat, LangGraph Agent, MCP Tool 연동 |
| 양도영 | 기획·문서 — 서비스 흐름 정리, README, 발표 자료 |

---

## 📄 License & References (라이선스 & 참고 문서)

| 문서 | 링크 |
|---|---|
| 국가법령정보센터 | https://www.law.go.kr |
| LangGraph 공식 문서 | https://langchain-ai.github.io/langgraph/ |
| Memgraph 공식 문서 | https://memgraph.com/docs |
| MCP (Model Context Protocol) | https://modelcontextprotocol.io |
| OpenRouter | https://openrouter.ai |
| Backend 상세 README | [backend/README.md](backend/README.md) |
| RAG 서브시스템 README | [rag/README.md](rag/README.md) |
| RAG Backend README | [rag/be/README.md](rag/be/README.md) |
| Infra README | [infra/README.md](infra/README.md) |
| Streamlit README | [streamlit/README.md](streamlit/README.md) |

> 이 레포지터리의 코드는 SK Networks AI Camp 28기 교육 과정 중 제작된 팀 프로젝트 산출물입니다.
