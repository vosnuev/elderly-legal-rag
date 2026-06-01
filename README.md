# 🧭 SKN28-3rd-1Team

> 노인·고령층을 위한 법률 정보를 쉽고 신뢰할 수 있게 찾도록 돕는 Agentic RAG + GraphRAG 기반 상담 서비스

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-Settings-E92063?logo=pydantic&logoColor=white)
![uv](https://img.shields.io/badge/uv-Python%20Tooling-6E56CF)
![LangChain](https://img.shields.io/badge/LangChain-Agent-1C3C3C?logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-1C3C3C?logo=langchain&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-LLM%20Gateway-111827)
![LangSmith](https://img.shields.io/badge/LangSmith-Tracing-1C3C3C?logo=langchain&logoColor=white)
![React](https://img.shields.io/badge/React-UI-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-Frontend-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-Build-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-Style-06B6D4?logo=tailwindcss&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Prototype-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data-150458?logo=pandas&logoColor=white)
![Memgraph](https://img.shields.io/badge/Memgraph-GraphRAG-FF6B35?logo=memgraph&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Infra-2496ED?logo=docker&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-Collaboration-181717?logo=github&logoColor=white)
![Linear](https://img.shields.io/badge/Linear-Project%20Tracking-5E6AD2?logo=linear&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-Docs-000000?logo=notion&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-Communication-5865F2?logo=discord&logoColor=white)

## 1. 👥 팀 소개 및 일정 계획

### 1) 팀 소개

| 이름 | 역할 | 한 일 |
| --- | --- | --- |
| 👑 이원빈 | 팀장 | 전체 일정 관리, 작업 방향 컨펌, 파트별 진행 상황 확인 |
| 📚 김지효 | RAG | 노인·고령층 관련 법령 데이터 확인, 문서 전처리와 임베딩 흐름 정리 |
| 🖥️ 송윤경 | 프론트엔드 | 사용자 질문 화면 구성, API 연결 흐름 설계, 결과 화면 UX 정리 |
| ⚙️ 전하영 | 백엔드 | FastAPI `/chat` 구성, LangGraph Agent 실행 구조 정리, MCP tool 연동 준비 |
| 🧭 양도영 | 기획·문서 | 전체 서비스 흐름 정리, README와 발표 자료 구성, 팀 산출물 내용 정리 |

### 2) 일정 계획

| 기간 | 주요 작업 | 상태 |
| --- | --- | --- |
| 2026-05-22 ~ 2026-05-26 | 주제 범위 확정, 고령층 법령 데이터 후보 정리 | 완료 |
| 2026-05-27 ~ 2026-05-29 | Backend API 계약, RAG POC, 화면 UX 설계 | 완료 |
| 2026-06-01 ~ 2026-06-03 | Backend, Streamlit, RAG MCP 연결 흐름 통합 검증 | 진행 예정 |
| 2026-06-04 | 전체 기능 연동, 통합 테스트, 발표와 시연 준비 | 목표 마감 |

## 2. 📌 프로젝트 소개

### 1) 주제

이 프로젝트는 노인과 고령층이 법률, 기초연금, 고령자 고용, 근로 관련 정보를 자연어로 질문하고, 실제 공공 문서와 법령을 근거로 답변을 받을 수 있도록 만드는 RAG 기반 상담 서비스입니다.

노인복지법, 기초연금법, 고령자고용촉진 관련 법령, 근로기준법 같은 문서는 국가법령정보센터와 관련 기관 자료에 흩어져 있습니다. 또한 법률·행정 문서는 용어가 어렵고 조건이 복잡해 사용자가 본인에게 맞는 정보를 빠르게 찾기 어렵습니다.

이 서비스는 문서 검색(Retrieval)과 LLM 답변 생성(Generation)을 결합해 사용자가 이해하기 쉬운 말로 답변하고 근거 문서까지 함께 확인할 수 있도록 설계합니다.

### 2) 핵심 목표

| 목표 | 설명 |
| --- | --- |
| 🔎 문서 기반 검색 | 노인·고령층 관련 법령과 행정 안내문을 검색 가능한 형태로 정리합니다. |
| 🧠 Agentic RAG 답변 | Main Agent가 질문을 판단하고 필요한 경우 RAG MCP Tool을 호출합니다. |
| 🧾 근거 중심 응답 | RAG 검색 결과와 출처를 바탕으로 답변합니다. |
| 💬 상담형 화면 | Streamlit 프로토타입으로 질문 입력부터 답변 확인까지 검증합니다. |
| 📈 추적 가능성 | LangSmith로 LLM 호출과 tool calling 과정을 확인합니다. |

## 3. 🎯 해결하려는 문제

### 1) 정보 접근 문제

| 문제 | 설명 |
| --- | --- |
| 정보가 흩어져 있음 | 노인복지, 기초연금, 고령자 고용, 근로 관련 정보가 여러 기관에 나뉘어 있어 한 번에 찾기 어렵습니다. |
| 용어가 어려움 | 법령과 행정 문서는 일반 사용자가 바로 이해하기 어렵습니다. |
| 최신성이 중요함 | 연금 기준, 지원 금액, 고용 기준은 바뀔 수 있어 최신 문서 확인이 필요합니다. |
| 잘못된 답변 위험 | 복지·법률 정보는 잘못 안내되면 실제 불이익으로 이어질 수 있습니다. |

### 2) RAG가 필요한 이유

일반 LLM은 학습된 지식만으로 답변하기 때문에 최신 법령, 기초연금 신청 기준, 고령자 고용 기준을 정확히 보장하기 어렵습니다. 이 프로젝트는 실제 문서를 먼저 찾고, 그 문서를 바탕으로 답변하는 구조를 사용합니다.

## 4. 🙋 주요 사용자

### 1) 사용자 유형

| 사용자 | 필요한 정보 |
| --- | --- |
| 👵 노인·고령층 당사자와 가족 | 기초연금, 노인복지, 신청 조건, 권리 보호 절차 |
| 🧑‍💼 복지사 및 상담 실무자 | 상담 중 빠르게 확인할 수 있는 법령, 지침, 공공 문서 근거 |
| 🏢 고령자 고용 관련 실무자 | 고령자 고용, 연령차별, 근로 기준 관련 법령 |

### 2) 질문 예시

```text
"65세 이상 노인이 받을 수 있는 혜택은 뭐가 있어?"
"기초연금 신청 방법과 준비 서류를 알려줘."
"노인일자리 신청은 어디에서 할 수 있어?"
"고령자가 나이 때문에 채용에서 차별받으면 어떻게 대응해야 해?"
"퇴직금을 못 받았을 때 어떤 법을 확인해야 해?"
```

## 5. 🧭 서비스 흐름

### 1) 전체 흐름

```text
사용자 질문
  -> Frontend 또는 Streamlit 화면
  -> Backend FastAPI /chat
  -> LangChain + LangGraph Agent
  -> RAG MCP Tool Server
  -> Memgraph 기반 문서 검색
  -> OpenRouter LLM 답변 생성
  -> 출처와 함께 화면에 표시
```

### 2) 역할 분리

| 영역 | 역할 |
| --- | --- |
| Frontend / Streamlit | 사용자가 질문하고 답변을 확인하는 인터페이스 |
| Backend | API 서버와 Main Agent Orchestrator 역할 |
| RAG Backend | Backend 내부 모듈이 아닌 별도 서비스로 동작하며 문서 ingest, 검색 API, MCP endpoint 제공 |
| Memgraph | GraphRAG 검색을 위한 그래프 데이터 저장 |
| Docs Web | 프로젝트 소개와 파트별 진행 방향 문서화 |

### 3) 아키텍처 원칙

| 원칙 | 설명 |
| --- | --- |
| 🧩 영역 분리 | Frontend, Backend, RAG를 독립된 영역으로 나누어 책임을 분리합니다. |
| 🐳 컨테이너 기반 실행 | 각 영역은 독립적인 Docker Container로 구성하고, 전체 실행은 Docker Compose로 묶는 방향입니다. |
| 🧠 Main Agent 중심 | Backend의 Main Agent가 사용자 요청을 판단하고 답변 흐름을 조율합니다. |
| 🛠️ MCP Tool 호출 | Main Agent는 RAG 내부 구현을 직접 알지 않고 MCP Tool 형태로 검색 기능을 호출합니다. |
| 🕸️ GraphRAG 확장 | RAG 영역은 문서 검색뿐 아니라 Memgraph 기반 관계 검색까지 확장할 수 있도록 설계합니다. |

## 6. ✨ 주요 기능

### 1) 사용자 기능

| 기능 | 설명 |
| --- | --- |
| 💬 자연어 상담 | 사용자가 어려운 법률 용어 없이 질문할 수 있습니다. |
| 🧾 근거 문서 제공 | 답변과 함께 관련 법령, 문서, 출처를 확인할 수 있도록 설계합니다. |
| 🔎 문서 검색 | 공공 문서와 법령을 기반으로 관련 정보를 찾습니다. |
| 📚 추가 판단 요소 안내 | 조건이 부족하면 추가 확인이 필요한 부분을 안내합니다. |

### 2) 개발 기능

| 기능 | 설명 |
| --- | --- |
| FastAPI `/chat` | 프론트엔드가 호출하는 메인 채팅 API입니다. |
| LangGraph Agent | `session_id` 기반으로 대화 흐름을 이어갈 수 있도록 구성합니다. |
| OpenRouter LLM | OpenRouter compatible `ChatOpenAI`로 LLM을 호출합니다. |
| MCP Tool | RAG 검색 기능을 Agent tool로 연결하기 위한 구조입니다. |
| LangSmith | LLM 호출과 tool calling trace를 검증합니다. |

## 7. ✅ 현재 구현 상태

### 1) 완료 및 진행 현황

| 영역 | 상태 |
| --- | --- |
| Backend `/chat` API | FastAPI에서 사용자 메시지를 받아 Agent 답변을 반환합니다. |
| OpenRouter 연동 | `langchain-openai`의 `ChatOpenAI`를 OpenRouter base URL로 사용합니다. |
| LangGraph Agent | `create_agent()`와 `InMemorySaver` 기반 session/thread 처리를 사용합니다. |
| LangSmith 검증 | LLM 호출 trace와 mock tool call trace를 확인했습니다. |
| RAG Backend | 문서 ingest, 검색 API, read-only MCP endpoint 구조가 있습니다. |
| RAG Frontend | 문서 목록, ingest job, review queue를 확인하는 운영 UI가 있습니다. |
| Streamlit | 상담 form, 채팅형 화면, backend `/chat` 연결 흐름을 검증합니다. |
| Docs Web | GitHub Pages 배포용 문서 웹 구조가 있습니다. |

### 2) 남은 작업

| 작업 | 설명 |
| --- | --- |
| 🔗 실제 RAG MCP 연결 | Backend Agent가 RAG MCP tool을 실제로 호출하도록 연결합니다. |
| 🧾 출처 응답 강화 | `sources`, `tool_calls`를 실제 검색 결과 기준으로 채웁니다. |
| 🧪 통합 테스트 | Streamlit, Backend, RAG Backend를 함께 실행해 전체 흐름을 검증합니다. |
| 🎤 시연 준비 | 질문 예시, 화면 흐름, LangSmith trace를 발표용으로 정리합니다. |

## 8. 🧰 기술 스택

### 1) 사용 기술

| 영역 | 사용 기술 |
| --- | --- |
| Backend | ![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white) ![Pydantic](https://img.shields.io/badge/Pydantic-Settings-E92063?logo=pydantic&logoColor=white) ![uv](https://img.shields.io/badge/uv-Package-6E56CF) |
| Agent | ![LangChain](https://img.shields.io/badge/LangChain-Agent-1C3C3C?logo=langchain&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-Flow-1C3C3C?logo=langchain&logoColor=white) ![OpenRouter](https://img.shields.io/badge/OpenRouter-LLM-111827) ![LangSmith](https://img.shields.io/badge/LangSmith-Trace-1C3C3C?logo=langchain&logoColor=white) |
| RAG | ![MCP](https://img.shields.io/badge/MCP-Tool%20Server-111827) ![Memgraph](https://img.shields.io/badge/Memgraph-Graph%20DB-FF6B35?logo=memgraph&logoColor=white) ![Neo4j](https://img.shields.io/badge/Neo4j-Compatible-4581C3?logo=neo4j&logoColor=white) ![GraphRAG](https://img.shields.io/badge/GraphRAG-Search-10B981) |
|Frontend | ![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-TS-3178C6?logo=typescript&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-Build-646CFF?logo=vite&logoColor=white) ![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-Style-06B6D4?logo=tailwindcss&logoColor=white) ![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-Components-000000?logo=shadcnui&logoColor=white) |
| Prototype | ![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-Data-150458?logo=pandas&logoColor=white) |
| Infra | ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white) ![Memgraph Lab](https://img.shields.io/badge/Memgraph%20Lab-Graph%20View-FF6B35?logo=memgraph&logoColor=white) ![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Docs%20Web-222222?logo=githubpages&logoColor=white) |
| Collaboration | ![GitHub](https://img.shields.io/badge/GitHub-Code-181717?logo=github&logoColor=white) ![Linear](https://img.shields.io/badge/Linear-Issues-5E6AD2?logo=linear&logoColor=white) ![Notion](https://img.shields.io/badge/Notion-Docs-000000?logo=notion&logoColor=white) ![Discord](https://img.shields.io/badge/Discord-Chat-5865F2?logo=discord&logoColor=white) |

## 9. 📁 프로젝트 구조

### 1) Repository Structure

```text
SKN28-3rd-1Team/
├── backend/                 # FastAPI 기반 Agent Orchestrator
│   ├── src/api/             # /chat API
│   ├── src/agent/           # LangGraph Agent, OpenRouter LLM, tools
│   └── src/prompt/          # Agent system prompt
├── rag/
│   ├── be/                  # RAG backend, ingest, search, MCP endpoint
│   ├── fe/                  # RAG 운영 UI
│   ├── infra/               # Memgraph, Memgraph Lab 실행 설정
│   └── docs/                # RAG 설계 문서
├── streamlit/               # 상담형 UI 프로토타입
├── docs_web/                # 프로젝트 소개용 문서 웹
├── docs/                    # 회의록, 온보딩, 개발 문서
├── frontend/                # 최종 프론트엔드 작업 공간
├── infra/                   # 루트 인프라 문서
├── AGENTS.md                # 협업 및 agent 작업 규칙
└── README.md
```

### 2) 주요 문서

| 문서 | 설명 |
| --- | --- |
| ⚙️ `backend/README.md` | Backend Agent 구조, `/chat` API, MCP 연결 위치 |
| 📚 `rag/README.md` | RAG 서브시스템 전체 구조 |
| 🛠️ `rag/be/README.md` | RAG Backend API, MCP endpoint, 환경 변수 |
| 🖥️ `rag/fe/README.md` | RAG 운영 UI 실행 방법 |
| 💬 `streamlit/README.md` | Streamlit 상담 UI 구조와 backend 연결 방법 |
| 📄 `docs_web/README.md` | 문서 웹 실행 및 GitHub Pages 배포 방식 |

## 10. 🚀 실행 방법

### 1) Backend Agent 실행

```bash
cd backend
cp .env.example .env
uv sync

set -a
source .env
set +a

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
  -d '{"session_id":"readme-test-1","message":"안녕. 너는 어떤 일을 할 수 있어?"}' \
  | python -m json.tool
```

### 2) Streamlit 상담 UI 실행

```bash
cd streamlit
cp .env.example .env
uv sync
uv run streamlit run streamlit.py
```

backend와 연결하려면 `streamlit/.env`에서 아래 값을 사용합니다.

```env
STREAMLIT_BACKEND_BASE_URL="http://127.0.0.1:8000"
STREAMLIT_CHAT_BACKEND_MOCK=false
```

### 3) RAG Infra 실행

```bash
cd rag
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

기본 접속 정보:

```text
Memgraph Bolt: bolt://127.0.0.1:7687
Memgraph Lab:  http://127.0.0.1:3000
```

### 4) RAG Backend 실행

```bash
cd rag/be
cp .env.example .env
uv sync
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8010
```

주요 endpoint:

```text
GET  /health
POST /ingest
POST /search
GET  /api/documents
POST /api/documents/search
GET  /api/review/edge-candidates
MCP  /mcp
```

### 5) RAG Frontend 실행

```bash
cd rag/fe
bun install
bun run dev
```

기본 접속:

```text
http://127.0.0.1:5173
```

### 6) Docs Web 실행

```bash
cd docs_web
npm install
npm run dev
```

## 11. 🧪 검증 방법

### 1) Backend

```bash
cd backend
PYTHONPATH=src uv run python -m compileall src scripts tests
PYTHONPATH=src uv run python -m unittest discover -s tests
```

### 2) RAG Backend

```bash
cd rag/be
PYTHONPATH=src uv run python -m compileall src tests
PYTHONPATH=src uv run python -m unittest discover -s tests
```

### 3) RAG Frontend

```bash
cd rag/fe
bun run lint
bun run build
```

### 4) Docs Web

```bash
cd docs_web
npm run lint
npm run build
```

## 12. 🔐 환경 변수 관리

### 1) 관리 원칙

- 실제 `.env` 파일은 Git에 올리지 않습니다.
- 각 서비스 디렉터리의 `.env.example`을 복사해 로컬에서만 값을 채웁니다.
- API key, DB URL, LangSmith key는 로컬 `.env`에서 관리합니다.

### 2) 서비스별 환경 파일

| 서비스 | 예시 파일 | 주요 값 |
| --- | --- | --- |
| Backend | `backend/.env.example` | OpenRouter API key, LangSmith 설정, CORS, RAG MCP URL |
| Streamlit | `streamlit/.env.example` | Backend API 주소, mock mode 여부 |
| RAG Backend | `rag/be/.env.example` | Memgraph 연결, MCP endpoint, 모델 설정 |
| RAG Frontend | `rag/fe/.env.example` | RAG API base URL |
| RAG Infra | `rag/infra/.env.example` | Memgraph 포트, Lab 포트 |

## 13. 🤝 협업 방식

### 1) 작업 관리

| 도구 | 사용 목적 |
| --- | --- |
| GitHub | 코드 관리, PR, 리뷰 |
| Linear | 파트별 일정과 이슈 관리 |
| Notion | 회의 내용, 기획 문서, 프로젝트 정리 |
| Discord | 실시간 소통 |

### 2) Git 규칙

- `main` 브랜치에 직접 push하지 않습니다.
- 기능, 수정, 문서 작업은 별도 브랜치에서 진행합니다.
- PR에는 변경 요약, 테스트 결과, 영향 디렉터리, 환경 변수 변경 여부를 기록합니다.
- 상세 작업 규칙은 `AGENTS.md`와 `docs/agent_workspace_guidelines.md`를 따릅니다.

## 14. 📝 한 줄 정리

### 1) 프로젝트 요약

이 프로젝트는 흩어진 노인·고령층 관련 법률 문서를 RAG로 찾고, Agent가 그 근거를 바탕으로 사용자가 이해하기 쉬운 상담 답변을 제공하는 서비스입니다.
