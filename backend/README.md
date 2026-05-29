# ⚙️ Backend Agent Orchestrator

FastAPI 기반 Agent Orchestrator 서버이다.

Frontend는 `POST /chat`으로 사용자 메시지를 보내고, backend는 LangChain Agent를 실행한 뒤 최종 자연어 답변을 `answer`로 반환한다. 파일 업로드, RAG ingest, ASR/audio 처리는 backend 책임에서 제외한다.

## ✨ 한눈에 보기

| 구분 | 내용 |
| --- | --- |
| 🚪 API 입구 | `POST /chat` |
| 🧠 LLM | OpenRouter 기반 `ChatOpenAI`, Cerebras primary provider |
| 🧩 Agent | LangChain `create_agent()` + LangGraph checkpointer |
| 🛠️ Tool | `agent/tool.py`에서 관리 |
| 📚 RAG | 추후 FastMCP Tool Server로 연결 |
| 💬 응답 | 자연스러운 한국어 `answer` 반환 |

## 🎯 현재 목표

기존의 `질문 분기 + schemas + 파일/RAG ingest + 자체 세션/rate limit` 구조를 다음 구조로 단순화한다.

```text
Frontend
  -> 🚪 POST /chat
  -> ⚡  FastAPI chat router
  -> 🧠 Main Agent Orchestrator
  -> 🔗 ChatOpenAI + LangChain tools
  -> 📚 MCP RAG tool server, later
  -> 💬 answer
```

## 🗂️ BACKEND 구조

```text
backend/
├── README.md                         # 안내 문서
├── pyproject.toml                    # 의존성
├── .env.example                      # 환경 변수 예시
├── scripts/                          # 수동 테스트
│   └── manual_chat.py                # /chat 테스트
├── src/                              # 앱 소스
│   ├── app.py                        # FastAPI 시작점
│   ├── logger.py                     # 로그 설정
│   ├── settings.py                   # 설정 로딩
│   ├── api/                          # API 라우터
│   │   ├── __init__.py               # 패키지 파일
│   │   └── chat.py                   # /chat API
│   ├── agent/                        # Agent 구성
│   │   ├── __init__.py               # 패키지 파일
│   │   ├── graph.py                  # Agent 실행
│   │   ├── openrouter_llm.py         # LLM 생성
│   │   └── tool.py                   # Tool 목록
│   └── prompt/                       # Prompt
│       ├── __init__.py               # export
│       ├── prompt_loader.py          # Prompt 렌더링
│       └── system_prompt.j2          # System prompt
└── tests/                            # 테스트
    └── test_backend_core.py          # 핵심 테스트
```

## 🧭 파일별 역할

| 파일 | 역할 |
| --- | --- |
| 🚀 `src/app.py` | FastAPI 앱 생성, CORS 설정, `/health`, router 등록 |
| 🚪 `src/api/chat.py` | `/chat` endpoint와 최소 Pydantic request/response 모델 |
| 🧠 `src/agent/graph.py` | `create_agent()` 기반 Main Agent Orchestrator |
| 🔑 `src/agent/openrouter_llm.py` | OpenRouter 호환 `ChatOpenAI` 생성 |
| 🛠️ `src/agent/tool.py` | Agent에 붙일 LangChain tool 목록 관리 |
| 🧾 `src/prompt/prompt_loader.py` | Jinja2 prompt 렌더링 |
| 💬 `src/prompt/system_prompt.j2` | Agent system prompt |
| ⚙️ `src/settings.py` | `BACKEND_` prefix 환경 변수 로딩 |
| 🧪 `scripts/manual_chat.py` | 터미널에서 `/chat`을 직접 호출하는 수동 테스트 스크립트 |
| ✅ `tests/test_backend_core.py` | health와 `/chat` 최소 동작 unittest |

## 🔄 Runtime 흐름

1. `src/app.py`가 FastAPI 앱을 만들고 `api.chat.router`를 등록한다.
2. Frontend가 `POST /chat`으로 `message`를 보낸다.
3. `src/api/chat.py`가 `ChatRequest`를 검증하고 `run_agent(request.message, session_id=...)`를 호출한다.
4. `src/agent/graph.py`가 `create_agent()`와 `InMemorySaver` checkpointer로 Agent를 만든다.
5. Agent는 `get_chat_llm()`, `get_tools()`, `render_prompt("system_prompt.j2")`를 조합한다.
6. `src/agent/openrouter_llm.py`가 OpenRouter API key와 provider routing으로 `ChatOpenAI`를 생성한다.
7. `src/agent/tool.py`가 현재는 placeholder `rag_search_tool`을 반환한다.
8. Agent 실행 결과의 마지막 assistant message를 `answer` 문자열로 반환한다.
9. `/chat` endpoint가 `{ "answer": "...", "tool_calls": [], "sources": [] }` 형태로 응답한다.

## 🖥️ Frontend 연결 위치

Frontend는 RAG 서버나 LLM을 직접 호출하지 않고 backend의 `/chat`만 호출한다.

| 구분 | backend 파일 | frontend에서 할 일 |
| --- | --- | --- |
| endpoint | `src/api/chat.py` | `POST /chat`으로 `message` 전송 |
| CORS | `src/settings.py` | frontend 주소가 `BACKEND_CORS_ORIGINS`에 포함되어 있는지 확인 |
| 앱 등록 | `src/app.py` | 별도 작업 없음. `app.include_router(chat_router)`로 이미 등록됨 |
| loading UI | frontend 코드 | 요청 시작 후 응답 전까지 “답변 생성중입니다...” 표시 |

Frontend 요청 예시는 다음과 같다.

```ts
// frontend에서 backend /chat으로 사용자 메시지를 전송한다.
async function sendChat(message: string) {
  const response = await fetch("http://127.0.0.1:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: "browser-session-id",
      metadata: { source: "frontend" },
    }),
  });

  return response.json();
}
```

“답변 생성중입니다...” 같은 문구는 frontend loading state로 처리한다. 현재 backend는 streaming이 아니라 Agent 실행이 끝난 뒤 한 번에 응답한다.

## 📚 RAG/MCP 연결 위치

RAG는 별도 FastMCP Tool Server가 담당하고, backend는 MCP Client로 tool만 가져와 Agent에 붙인다.

| 구분 | backend 파일 | 해야 할 일 |
| --- | --- | --- |
| MCP 서버 URL | `src/settings.py` | `settings.rag_mcp_url` 값 사용 |
| 환경 변수 | `.env` | `BACKEND_RAG_MCP_URL="http://127.0.0.1:8010/mcp"` 설정 |
| tool 연결 | `src/agent/tool.py` | placeholder `rag_search_tool` 대신 MCP tools 반환 |
| Agent 연결 | `src/agent/graph.py` | `create_agent(..., tools=get_tools(), ...)`에 MCP tools 전달 |
| 응답 출처 | `src/api/chat.py` | 필요 시 `sources`, `tool_calls` 채우도록 확장 |

현재 `langchain_mcp_adapters.client.MultiServerMCPClient.get_tools()`는 async 함수다. 실제 MCP 연결 단계에서는 `get_tools()`와 `run_agent()`를 async 흐름으로 바꾸거나, 앱 시작 시 MCP tools를 로딩해 캐싱하는 방식 중 하나를 선택해야 한다.

예상 연결 형태는 다음과 같다.

```python
# MCP 서버에서 RAG tool 목록을 가져온다.
client = MultiServerMCPClient(
    {
        "rag": {
            "transport": "streamable_http",
            "url": settings.rag_mcp_url,
        }
    }
)

# Agent에 붙일 MCP tools를 로딩한다.
tools = await client.get_tools(server_name="rag")
```

파일을 주고 그 안에서 검색하라는 요구는 RAG 영역이다. 파일 업로드, 문서 파싱, chunking, embedding, vector DB 저장은 MCP RAG Tool Server가 처리하고, backend는 검색 tool 호출과 최종 답변 orchestration만 담당한다.

## 🚀 Backend 실행 진입점

backend 실행 진입점은 `src/app.py`이다.

| 구분 | 값 |
| --- | --- |
| 실행 파일 | `src/app.py` |
| FastAPI app 객체 | `app` |
| uvicorn import 경로 | `app:app` |
| 실행 기준 디렉터리 | `backend/` |

`PYTHONPATH=src`를 붙이는 이유는 `src/app.py`를 `app` 모듈로 import하기 위해서다.

```bash
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8000
```

`src/app.py` 안의 `main()`을 직접 실행하는 방식도 가능하다.

```bash
PYTHONPATH=src uv run python src/app.py
```

개발 중 자동 reload가 필요하면 `.env`의 `BACKEND_RELOAD=true`를 사용하거나 uvicorn에 `--reload`를 붙인다.

## 💬 Chat API

### POST `/chat`

요청:

```json
{
  "session_id": "optional-session-id",
  "message": "노인일자리 신청 방법 알려줘",
  "metadata": {
    "source": "frontend"
  }
}
```

응답:

```json
{
  "answer": "신청 방법은 지역과 사업 유형에 따라 달라질 수 있어요...",
  "tool_calls": [],
  "sources": []
}
```

`session_id`는 LangGraph `thread_id`로 전달된다. 같은 `session_id`로 요청하면 프로세스가 살아 있는 동안 `InMemorySaver` checkpointer가 같은 대화 이력을 이어간다. `session_id`가 없으면 요청마다 익명 thread를 새로 만들어 세션 간 이력이 섞이지 않게 처리한다.

## 🧾 Prompt

프롬프트는 Markdown 파일이 아니라 Jinja2 템플릿을 사용한다.

- `render_prompt("system_prompt.j2")`로 system prompt를 렌더링한다.
- 보기 생성 여부는 backend 분기 코드가 아니라 LLM이 답변 맥락에 따라 판단한다.
- tool 사용 여부도 LLM이 system prompt와 tool description을 보고 판단한다.
- frontend component, JSON UI, API schema를 생성하지 않도록 system prompt에 명시한다.

## 🛠️ Tools and MCP

현재 `src/agent/tool.py`에는 MCP 연결 전 placeholder인 `rag_search_tool`만 있다. 실제 RAG 연결은 위의 `RAG/MCP 연결 위치` 섹션 기준으로 `src/agent/tool.py`에서 MCP tools를 가져오도록 바꾸면 된다.

## 🔐 환경 변수

`.env`는 `backend/.env`에 둔다. 커밋하지 않는다.

```bash
cp .env.example .env
```

주요 값:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | 빈 값 | 실제 `/chat` 호출에 필요한 OpenRouter API 키 |
| `BACKEND_OPENROUTER_MODEL` | `openai/gpt-oss-120b` | 사용할 LLM 모델 |
| `BACKEND_OPENROUTER_PROVIDER_ORDER` | `["cerebras"]` | 우선 시도할 OpenRouter provider 순서 |
| `BACKEND_OPENROUTER_ALLOW_FALLBACKS` | `true` | primary provider 실패 시 OpenRouter fallback 허용 여부 |
| `BACKEND_API_HOST` | `127.0.0.1` | backend bind host |
| `BACKEND_API_PORT` | `8000` | backend 서버 포트 |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:8501","http://127.0.0.1:8501","http://localhost:5173","http://localhost:3000"]` | 허용할 frontend origin |
| `BACKEND_LLM_TEMPERATURE` | `0.2` | LLM temperature |
| `BACKEND_LLM_TIMEOUT_MS` | `60000` | LLM timeout |
| `BACKEND_LLM_MAX_RETRIES` | `2` | LLM 재시도 횟수 |
| `BACKEND_RAG_MCP_URL` | `http://127.0.0.1:8010/mcp` | RAG MCP Tool Server URL |
| `BACKEND_TOOL_TIMEOUT_MS` | `30000` | tool 실행 timeout |

`.env.example`에는 로컬에서 자주 바꿔야 하는 값만 남겼다. 서비스 이름/버전, OpenRouter base URL/app title은 코드 기본값을 사용한다.

## ✅ 검증 방법

아래 명령은 모두 `backend` 디렉터리에서 실행한다.

### 1. 의존성 동기화

```bash
uv sync
```

### 2. 정적 import와 문법 확인

```bash
PYTHONPATH=src uv run python -m compileall src scripts tests
```

성공하면 `Compiling ...` 또는 `Listing ...`만 출력되고 에러 없이 종료된다.

### 3. unittest 실행

```bash
PYTHONPATH=src uv run python -m unittest discover -s tests
```

현재 테스트는 다음을 확인한다.

- `/health`가 `status: ok`를 반환한다.
- `/chat`이 `run_agent()` 결과를 `answer`로 반환한다.

### 4. 서버 실행

```bash
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8000
```

정상 실행 시 아래와 비슷한 로그가 나온다.

```text
Uvicorn running on http://127.0.0.1:8000
```

종료는 서버 터미널에서 `Ctrl+C`를 누른다.

### 5. health curl 확인

다른 터미널에서 실행한다.

```bash
curl -s http://127.0.0.1:8000/health
```

기대 응답:

```json
{"status":"ok","service":"SKN28 Backend","version":"0.1.0"}
```

### 6. chat curl 확인

실제 LLM 호출이므로 `.env`에 `OPENROUTER_API_KEY`가 필요하다.

```bash
curl -s http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"노인일자리 신청 방법 알려줘"}'
```

기대 응답 형태:

```json
{
  "answer": "LLM이 생성한 한국어 답변",
  "tool_calls": [],
  "sources": []
}
```

현재 RAG MCP tool은 아직 연결 전이다. LLM이 `rag_search_tool`을 호출하면 “RAG 검색 도구는 아직 연결되지 않았습니다.”라는 placeholder 결과를 참고할 수 있다.

### 7. 터미널 수동 테스트

```bash
PYTHONPATH=src uv run python scripts/manual_chat.py
```

수동 테스트는 `/chat`에 직접 요청을 보내고 `answer`, `tool_calls`, `sources`를 터미널에 출력한다.

## 🧯 자주 나는 문제

| 증상 | 확인할 것 |
| --- | --- |
| `/chat`이 500을 반환 | `.env`의 `OPENROUTER_API_KEY` 설정 여부 |
| `/health` 연결 실패 | uvicorn이 켜져 있는지, 포트가 `8000`인지 확인 |
| `Address already in use` | 이미 8000 포트를 쓰는 서버 종료 또는 `--port 8001` 사용 |
| RAG 근거가 안 붙음 | 아직 MCP RAG tool 연결 전 상태인지 확인 |
| frontend에서 CORS 오류 | `BACKEND_CORS_ORIGINS`에 frontend 주소 추가 |

## ☑️ 검증 체크리스트

- `uv sync` 성공
- `compileall` 성공
- `unittest` 성공
- `GET /health`가 200 반환
- `POST /chat`이 `answer` 필드를 포함한 200 반환
- 같은 `session_id`로 연속 요청 시 같은 LangGraph thread를 사용
- `schemas`, `mock`, `session_store.py`, `rate_limiter.py` import가 남아 있지 않음

남은 구현 작업은 MCP RAG tool을 `src/agent/tool.py`에 연결하고, 필요하면 in-memory checkpointer를 영속 저장소 기반 checkpointer로 교체하는 것이다.
