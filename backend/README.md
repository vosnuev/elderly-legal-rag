# ⚙️ Backend Agent Orchestrator

FastAPI 기반 Agent Orchestrator 서버이다.

Frontend는 `POST /chat`으로 최종 JSON 응답을 받을 수 있고, `POST /chat/stream`으로 생성 중인 답변 조각을 SSE로 받을 수 있다. Backend는 LangChain Agent를 실행한 뒤 자연어 답변을 `answer`로 반환한다. 파일 업로드, RAG ingest, ASR/audio 처리는 backend 책임에서 제외한다.

## ✨ 한눈에 보기

| 구분 | 내용 |
| --- | --- |
| 🚪 API 입구 | `POST /chat`, `POST /chat/stream` |
| 🧠 LLM | OpenRouter 기반 `ChatOpenAI`, Cerebras primary provider |
| 🧩 Agent | LangChain `create_agent()` + LangGraph checkpointer |
| 🛠️ Tool | `agent/tool.py`에서 관리 |
| 📚 RAG | FastMCP Tool Server에서 read-only MCP tools 로딩 |
| 💬 응답 | 최종 JSON `answer` 또는 SSE `delta`/`final` 반환 |

## 🎯 현재 목표

기존의 `질문 분기 + schemas + 파일/RAG ingest + 자체 세션/rate limit` 구조를 다음 구조로 단순화한다.

```text
Frontend
  -> 🚪 POST /chat 또는 POST /chat/stream
  -> ⚡  FastAPI chat router
  -> 🧠 Main Agent Orchestrator
  -> 🔗 ChatOpenAI + LangChain tools
  -> 📚 MCP RAG tool server
  -> 💬 answer 또는 delta stream
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
| 🚪 `src/api/chat.py` | `/chat`, `/chat/stream` endpoint와 최소 Pydantic request/response 모델 |
| 🧠 `src/agent/graph.py` | `create_agent()` 기반 Main Agent Orchestrator와 streaming 실행 함수 |
| 🔑 `src/agent/openrouter_llm.py` | OpenRouter 호환 `ChatOpenAI` 생성 |
| 🛠️ `src/agent/tool.py` | Agent에 붙일 LangChain tool 목록 관리 |
| 🧾 `src/prompt/prompt_loader.py` | Jinja2 prompt 렌더링 |
| 💬 `src/prompt/system_prompt.j2` | Agent system prompt |
| ⚙️ `src/settings.py` | `BACKEND_` prefix 환경 변수 로딩 |
| 🧪 `scripts/manual_chat.py` | 터미널에서 `/chat`을 직접 호출하는 수동 테스트 스크립트 |
| ✅ `tests/test_backend_core.py` | health, `/chat`, `/chat/stream` 최소 동작 unittest |

## 🔄 Runtime 흐름

1. `src/app.py`가 FastAPI 앱을 만들고 `api.chat.router`를 등록한다.
2. Frontend가 `POST /chat` 또는 `POST /chat/stream`으로 `message`를 보낸다.
3. `src/api/chat.py`가 `ChatRequest`를 검증한다. `/chat`은 `run_agent(...)`, `/chat/stream`은 `run_agent_stream(...)`을 호출한다.
4. `src/agent/graph.py`가 `create_agent()`와 `InMemorySaver` checkpointer로 Agent를 만든다.
5. Agent는 `get_chat_llm()`, `get_tools()`, `render_prompt("system_prompt.j2")`를 조합한다.
6. `src/agent/openrouter_llm.py`가 OpenRouter API key와 provider routing으로 `ChatOpenAI`를 생성한다.
7. `src/agent/tool.py`가 RAG MCP server에서 read-only MCP tools를 비동기로 로딩하고 캐시한다.
8. 일반 요청에서는 Agent 실행 결과의 마지막 assistant message를 `answer` 문자열로 반환한다.
9. 스트리밍 요청에서는 생성 중인 text chunk를 `delta` 이벤트로 순차 전송하고, 마지막에 기존 `ChatResponse`와 호환되는 `final` 이벤트를 전송한다.

## 🖥️ Frontend 연결 위치

Frontend는 RAG 서버나 LLM을 직접 호출하지 않고 backend의 `/chat` 또는 `/chat/stream`만 호출한다.

| 구분 | backend 파일 | frontend에서 할 일 |
| --- | --- | --- |
| endpoint | `src/api/chat.py` | 최종 응답은 `POST /chat`, 스트리밍 응답은 `POST /chat/stream`으로 `message` 전송 |
| CORS | `src/settings.py` | frontend 주소가 `BACKEND_CORS_ORIGINS`에 포함되어 있는지 확인 |
| 앱 등록 | `src/app.py` | 별도 작업 없음. `app.include_router(chat_router)`로 이미 등록됨 |
| loading UI | frontend 코드 | `/chat`은 응답 대기 상태를 표시하고, `/chat/stream`은 `delta`를 받을 때마다 답변을 단계적으로 표시 |

최종 JSON 응답을 받는 요청 예시는 다음과 같다.

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

스트리밍 UI가 필요한 frontend는 `/chat/stream`을 호출하고 `text/event-stream` 응답의 `delta` 이벤트를 누적해서 표시한다. `/chat`은 기존 호환성을 위해 최종 JSON 응답 계약을 유지한다.

## 📚 RAG/MCP 연결 위치

RAG는 별도 FastMCP Tool Server가 담당하고, backend는 MCP Client로 tool만 가져와 Agent에 붙인다.

| 구분 | backend 파일 | 동작 |
| --- | --- | --- |
| MCP 서버 URL | `src/settings.py` | `settings.rag_mcp_url` 값 사용 |
| 환경 변수 | `.env` | 로컬은 `BACKEND_RAG_MCP_URL="http://127.0.0.1:8010/mcp/"`, Docker network 내부는 `http://rag-be:8010/mcp/` 사용 |
| tool 연결 | `src/agent/tool.py` | `MultiServerMCPClient`로 MCP tools를 async 로딩하고 캐시 |
| Agent 연결 | `src/agent/graph.py` | `create_agent(..., tools=await get_tools(), ...)`에 MCP tools 전달 |
| 응답 출처 | `src/api/chat.py` | 필요 시 `sources`, `tool_calls` 채우도록 확장 |

`langchain_mcp_adapters.client.MultiServerMCPClient.get_tools()`와 MCP tool
호출은 async 경로를 사용한다. 그래서 `/chat`과 `/chat/stream`도 agent를
`ainvoke()` / `astream()`으로 실행한다. MCP 원본 tool 이름은
`memgraph.read_query`처럼 점을 포함하므로, LangChain/OpenAI tool 이름은
`memgraph_read_query`처럼 안전한 이름으로 치환한다. 실제 MCP call은 원본
tool 이름으로 전달된다.

연결 형태는 다음과 같다.

```python
# MCP 서버에서 RAG tool 목록을 가져온다.
client = MultiServerMCPClient(
    {
        "rag": {
            "transport": "http",
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

### POST `/chat/stream`

요청 body는 `/chat`과 동일하다.

```json
{
  "session_id": "optional-session-id",
  "message": "노인일자리 신청 방법 알려줘",
  "metadata": {
    "source": "frontend"
  }
}
```

응답은 SSE(`text/event-stream`) 형식이다. 생성 중에는 `delta` 이벤트가 여러 번 전송되고, 완료 시 `final` 이벤트가 한 번 전송된다.

```text
event: delta
data: {"content": "신청은 "}

event: delta
data: {"content": "주민센터에서 "}

event: final
data: {"answer": "신청은 주민센터에서 할 수 있습니다.", "tool_calls": [], "sources": []}
```

`final` 이벤트의 data는 기존 `ChatResponse`와 같은 필드(`answer`, `tool_calls`, `sources`)를 사용한다. `session_id`는 `/chat`과 동일하게 LangGraph `thread_id`로 전달되므로 같은 세션의 대화 문맥이 이어진다.

## 🧾 Prompt

프롬프트는 Markdown 파일이 아니라 Jinja2 템플릿을 사용한다.

- `render_prompt("system_prompt.j2")`로 system prompt를 렌더링한다.
- 보기 생성 여부는 backend 분기 코드가 아니라 LLM이 답변 맥락에 따라 판단한다.
- tool 사용 여부도 LLM이 system prompt와 tool description을 보고 판단한다.
- frontend component, JSON UI, API schema를 생성하지 않도록 system prompt에 명시한다.

## 🛠️ Tools and MCP

`src/agent/tool.py`는 RAG Backend의 FastMCP endpoint에서 아래 read-only MCP
tools를 로딩한다.

- `memgraph_read_query`
- `memgraph_vector_search`
- `memgraph_text_index_search`
- `memgraph_graph_traverse`
- `memgraph_schema_read`

원본 MCP tool 이름은 `memgraph.read_query` 형식이고, LangChain/OpenAI에
전달하는 이름만 안전한 snake style로 바꾼다.

RAG 없이 main model만 확인해야 하는 경우에는 `BACKEND_ENABLE_RAG_TOOLS=false`로
실행한다. 이때 agent에는 빈 tool 목록이 전달되므로 RAG MCP 서버가 떠 있지
않아도 `/chat` 호출 경로를 확인할 수 있다.

## 📊 벤치마크 결과 위치

backend 안의 `scripts/`는 현재 수동 `/chat` 테스트용 `manual_chat.py`만 유지한다. 벤치마크 실행/변환/LangSmith 검증용 임시 스크립트는 backend 서비스 코드 안에 두지 않고, 발표와 검증에 사용할 결과 산출물은 repo 루트의 `presentation/test-data/no-tool-benchmark/`에 정리했다.

주요 산출물:

| 파일 | 내용 |
| --- | --- |
| `../presentation/test-data/no-tool-benchmark/no_tool_benchmark_report.md` | model/provider별 no_tool 통합 분석 리포트 |
| `../presentation/test-data/no-tool-benchmark/artifacts/no_tool_combined_results.csv` | strict 기준으로 합친 원본 benchmark CSV |
| `../presentation/test-data/no-tool-benchmark/artifacts/no_tool_provider_summary.csv` | model/provider별 평균 token, 비용, latency 요약 |
| `../presentation/test-data/no-tool-benchmark/artifacts/no_tool_question_summary.csv` | 질문별 평균 token, 비용, latency 요약 |
| `../presentation/test-data/no-tool-benchmark/charts/*.png` | 비용, latency, token 비교 차트 |
| `../presentation/test-data/no-tool-benchmark/results/benchmark_all_model_by_provider.xlsx` | 전체 결과를 묶은 Excel 파일 |

비교 범위:

- no_tool 상태에서 동일한 360개 질문을 model/provider별로 비교했다.
- Qwen은 비용 문제로 제외했다.
- 비교한 항목은 성공/실패 수, input/output/used token, 질문당 평균 비용, 총 비용, 평균 latency, p95 latency, routing 일치 여부다.
- 답변 품질 평가는 별도 단계이므로, 현재 리포트는 비용/속도/token 중심의 운영 지표 비교로 봐야 한다.

## 🔐 환경 변수

`.env`는 `backend/.env`에 둔다. 커밋하지 않는다.

```bash
cp .env.example .env
```

주요 값:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `BACKEND_OPENROUTER_API_KEY` | 빈 값 | 실제 `/chat` 호출에 필요한 OpenRouter API 키. `OPENROUTER_API_KEY`도 호환된다. |
| `BACKEND_OPENROUTER_MODEL` | `openai/gpt-oss-120b` | 사용할 LLM 모델 |
| `BACKEND_OPENROUTER_PROVIDER_ORDER` | `["cerebras/fp16"]` | 우선 시도할 OpenRouter provider 순서 |
| `BACKEND_OPENROUTER_ALLOW_FALLBACKS` | `false` | primary provider 실패 시 OpenRouter fallback 허용 여부. benchmark 기준과 맞추기 위해 기본값은 `false` |
| `BACKEND_OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API base URL |
| `BACKEND_OPENROUTER_REQUIRE_PARAMETERS` | `false` | provider가 요청 parameter를 지원해야 하는지 여부 |
| `BACKEND_API_HOST` | `127.0.0.1` | backend bind host |
| `BACKEND_API_PORT` | `8000` | backend 서버 포트 |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:8501","http://127.0.0.1:8501","http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000","http://127.0.0.1:3000"]` | 허용할 frontend origin |
| `BACKEND_HOST_BIND` | `127.0.0.1` | Docker compose가 host에 공개할 bind 주소 |
| `BACKEND_HOST_PORT` | `8001` | Docker compose가 host에 공개할 포트 |
| `BACKEND_LLM_TEMPERATURE` | `0.2` | LLM temperature |
| `BACKEND_LLM_TIMEOUT_MS` | `60000` | LLM timeout |
| `BACKEND_LLM_MAX_RETRIES` | `2` | LLM 재시도 횟수 |
| `BACKEND_LLM_REASONING_EFFORT` | 빈 값 | 비워두면 OpenRouter 요청에서 `reasoning_effort`를 생략 |
| `BACKEND_RAG_MCP_URL` | `http://127.0.0.1:8010/mcp/` | RAG MCP Tool Server URL |
| `BACKEND_ENABLE_RAG_TOOLS` | `true` | `false`로 두면 RAG MCP tools를 로딩하지 않고 no-RAG/no-tool로 agent 실행 |
| `BACKEND_TOOL_TIMEOUT_MS` | `30000` | tool 실행 timeout |

실제 `backend/.env`는 Git에 커밋하지 않는다. `/health`는 키 없이도 동작하지만 `/chat`은 실제 LLM 호출이므로 `BACKEND_OPENROUTER_API_KEY`가 필요하다.

## 🐳 Docker 실행

다른 계정이나 다른 클라이언트에서 같은 backend에 붙어 개발할 때는 Docker compose로 backend를 띄운다.

```bash
cd backend
cp .env.example .env
# .env의 BACKEND_OPENROUTER_API_KEY를 실제 값으로 채운다.
docker compose up -d --build
```

기본값은 host의 `127.0.0.1:8001`을 컨테이너 내부 `8000`에 연결한다. 현재 개발 서버가 `8000`을 쓰고 있지 않다면 `.env`에서 `BACKEND_HOST_PORT=8000`으로 바꿔도 된다. 같은 서버 계정이나 VS Code/SSH port forwarding으로 붙는 개발자는 `127.0.0.1:8001`을 쓰면 된다. 서버 네트워크 인터페이스에 직접 공개해야 한다면 `.env`에서 `BACKEND_HOST_BIND=0.0.0.0`으로 바꾼다.

상태 확인:

```bash
curl -s http://127.0.0.1:8001/health
docker compose logs -f backend
```

RAG 없이 Qwen3.7 Max를 한 번 확인하려면 backend compose만 사용해서 아래처럼
띄운다. `infra/`의 compose 파일은 사용하지 않는다.

```bash
cd backend
BACKEND_HOST_PORT=8002 \
BACKEND_OPENROUTER_MODEL='qwen/qwen3.7-max' \
BACKEND_OPENROUTER_PROVIDER_ORDER='["alibaba"]' \
BACKEND_OPENROUTER_ALLOW_FALLBACKS=false \
BACKEND_ENABLE_RAG_TOOLS=false \
BACKEND_LLM_REASONING_EFFORT='' \
docker compose up -d --build backend

curl -s http://127.0.0.1:8002/health
curl -s http://127.0.0.1:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"qwen-no-rag-smoke","message":"근로기준법에서 근로자와 사용자 관련해서 기본적으로 어떤 내용을 확인해야 해? 5문장 이내로 답해줘."}'
```

이 스모크 테스트는 실제 OpenRouter 호출이므로 `backend/.env`의
`OPENROUTER_API_KEY` 또는 `BACKEND_OPENROUTER_API_KEY`가 유효해야 한다.

종료:

```bash
docker compose down
```

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
- `/chat/stream`이 `text/event-stream`으로 `delta`와 `final` 이벤트를 반환한다.

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

실제 LLM 호출이므로 `.env`에 `BACKEND_OPENROUTER_API_KEY`가 필요하다.

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

RAG MCP tools는 backend agent에 연결되어 있다. 실제 답변 생성과 tool
선택은 OpenRouter LLM 호출이므로 `.env`의 OpenRouter API key가 유효해야 한다.

### 7. chat stream curl 확인

실제 LLM 호출이므로 `.env`에 `BACKEND_OPENROUTER_API_KEY`가 필요하다. `--no-buffer`를 붙이면 curl이 받은 chunk를 바로 출력한다.

```bash
curl --no-buffer http://127.0.0.1:8000/chat/stream \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"manual-stream-session","message":"노인일자리 신청 방법을 5문장으로 알려줘"}'
```

기대 응답 형태:

```text
event: delta
data: {"content": "..."}

event: final
data: {"answer": "...", "tool_calls": [], "sources": []}
```

chunk가 실제로 여러 번 나뉘어 도착하는지 더 자세히 보려면 trace를 남긴다.

```bash
curl --no-buffer --trace-time --trace-ascii /tmp/chat_stream_trace.txt \
  http://127.0.0.1:8000/chat/stream \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"manual-stream-session","message":"노인일자리 신청 방법을 5문장으로 알려줘"}'
```

`/tmp/chat_stream_trace.txt`에 `Recv data`가 여러 번 기록되면 chunk가 나뉘어 수신된 것이다.

### 8. 터미널 수동 테스트

```bash
PYTHONPATH=src uv run python scripts/manual_chat.py
```

수동 테스트는 `/chat`에 직접 요청을 보내고 `answer`, `tool_calls`, `sources`를 터미널에 출력한다.

## 🧯 자주 나는 문제

| 증상 | 확인할 것 |
| --- | --- |
| `/chat`이 500을 반환 | `.env`의 `BACKEND_OPENROUTER_API_KEY` 설정 여부 |
| `/chat/stream`이 404를 반환 | 최신 backend 코드로 실행 중인지, 서버를 재시작했는지 확인 |
| `/chat/stream`이 한 번에만 출력됨 | 질문이 너무 짧은지 확인하고, `curl --no-buffer --trace-time`으로 실제 수신 chunk를 확인 |
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
- `POST /chat/stream`이 `text/event-stream`으로 `delta`와 `final` 이벤트 반환
- 같은 `session_id`로 연속 요청 시 같은 LangGraph thread를 사용
- `schemas`, `mock`, `session_store.py`, `rate_limiter.py` import가 남아 있지 않음

남은 구현 작업은 MCP RAG tool을 `src/agent/tool.py`에 연결하고, 필요하면 in-memory checkpointer를 영속 저장소 기반 checkpointer로 교체하는 것이다.
