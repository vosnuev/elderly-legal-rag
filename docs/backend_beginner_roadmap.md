# SKN28 3rd 1Team 백엔드 구조 잡기 초보자 로드맵

작성 기준: 2026-05-26, 현재 GitHub 저장소와 로컬 작업 폴더 기준

## 1. 이 프로젝트에서 백엔드가 맡는 역할

이 프로젝트는 장애인 및 취약계층 복지/법률 정보를 RAG로 답변하는 서비스입니다.

전체 흐름은 이렇게 보면 됩니다.

```text
Streamlit 또는 프론트엔드
-> FastAPI 백엔드
-> RAG 검색/Agent/LLM 처리
-> 구조화된 JSON 응답
-> 프론트엔드 화면 렌더링
```

백엔드는 여기서 중간 관리자 역할입니다.

- 사용자의 질문을 HTTP API로 받는다.
- 질문이 비어 있거나 형식이 잘못되면 막는다.
- RAG 또는 LLM Agent에 질문을 넘긴다.
- Agent가 만든 답변을 프론트가 쓰기 쉬운 JSON으로 정리한다.
- 에러가 나도 프론트가 깨지지 않도록 일정한 형식으로 응답한다.

처음부터 RAG, LangGraph, OpenRouter, 프론트 연결을 한 번에 다 하려고 하면 어렵습니다. 먼저 백엔드 API 모양을 안정적으로 만들고, 그 다음에 내부 처리 로직을 바꾸는 순서가 좋습니다.

## 2. 현재 저장소 상태 요약

현재 모노레포 구조는 대략 이렇게 나뉘어 있습니다.

```text
SKN28-3rd-1Team/
├── backend/    # FastAPI 메인 백엔드
├── rag/        # GraphRAG, 문서 파싱, 검색 작업
├── streamlit/  # Streamlit 기반 시연/프론트
├── frontend/   # 실제 프론트엔드 자리
├── docs_web/   # 문서 웹
├── infra/      # 인프라
└── docs/       # 문서
```

백엔드는 현재 기본 FastAPI 앱이 있습니다.

```text
backend/
├── src/
│   ├── app.py       # FastAPI 앱 생성, health API 있음
│   └── settings.py  # 환경변수 설정 로딩
├── pyproject.toml
├── uv.lock
└── .env.example
```

로컬 작업 폴더에는 아래 파일들도 이미 만들어져 있습니다. 대부분 아직 비어 있으므로, 이 파일들을 순서대로 채우면 됩니다.

```text
backend/src/
├── api/
│   ├── __init__.py
│   └── chat.py
├── schemas/
│   ├── __init__.py
│   └── chat.py
├── agent/
│   ├── __init__.py
│   ├── graph.py
│   └── openrouter_llm.py
├── prompt/
│   ├── __init__.py
│   ├── prompt_loader.py
│   └── system.md
├── logger.py
├── app.py
└── settings.py
```

주의할 점: 현재 `backend/src/prompt/system.md`는 "노인복지" 상담 Agent라고 되어 있습니다. 프로젝트 README의 주제는 "장애인 및 취약계층 복지/법률 RAG Agent"이므로, 나중에 프롬프트 주제를 맞춰야 합니다.

## 3. 백엔드 최소 시작 구조

처음부터 아래의 모든 파일을 다 채우려고 하면 복잡합니다.

초보자 기준 첫 시작은 이것만 있으면 됩니다.

```text
backend/
├── src/
│   ├── app.py
│   ├── settings.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py
│   └── schemas/
│       ├── __init__.py
│       └── chat.py
├── .env.example
├── pyproject.toml
└── uv.lock
```

첫 목표는 `POST /api/chat`이 mock JSON 응답을 반환하는 것입니다. 이 단계에서는 `agent/`, `prompt/`, `logger.py`, `tests/`를 아직 안 만들어도 됩니다.

나중에 LLM과 Agent를 붙일 때 아래 구조로 확장하면 됩니다.

```text
backend/
├── src/
│   ├── app.py
│   ├── settings.py
│   ├── logger.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── chat.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   └── openrouter_llm.py
│   └── prompt/
│       ├── __init__.py
│       ├── prompt_loader.py
│       └── system.md
├── tests/
│   ├── test_health.py
│   └── test_chat.py
├── .env.example
├── pyproject.toml
└── uv.lock
```

각 폴더의 역할은 이렇게 생각하면 됩니다.

| 위치 | 역할 |
| --- | --- |
| `app.py` | FastAPI 앱을 만들고 라우터를 연결하는 시작점 |
| `settings.py` | `.env` 값을 읽어서 설정 객체로 제공 |
| `api/chat.py` | `/api/chat` 같은 HTTP 엔드포인트 |
| `schemas/chat.py` | 요청/응답 JSON 모양을 Pydantic 모델로 정의 |
| `logger.py` | 로그 형식을 통일. 초반에는 없어도 됨 |
| `agent/openrouter_llm.py` | OpenRouter LLM 호출 담당 |
| `agent/graph.py` | LangGraph 또는 Agent 실행 흐름 담당 |
| `prompt/prompt_loader.py` | `system.md` 같은 프롬프트 파일 읽기 |
| `prompt/system.md` | Agent의 역할과 답변 원칙 |
| `tests/` | API가 깨지지 않는지 확인하는 테스트 |

`__init__.py`는 폴더 안에 들어가는 빈 Python 파일입니다. 예를 들어 `api` 폴더를 패키지처럼 쓰고 싶으면 `backend/src/api/__init__.py`를 둡니다.

Python 3.3 이후에는 `__init__.py`가 없어도 import가 되는 경우가 많지만, 초보자 프로젝트에서는 빈 파일로 만들어두는 편이 import 문제를 줄이기 쉽습니다. 단, `__init__.py` 안에 코드를 꼭 넣을 필요는 없습니다.

## 4. 가장 먼저 해야 할 일

첫 목표는 "진짜 RAG 답변"이 아닙니다.

첫 목표는 이것입니다.

```text
사용자가 질문을 보낸다
-> 백엔드 `/api/chat`이 받는다
-> mock 응답을 JSON으로 돌려준다
-> Streamlit이 그 JSON을 화면에 그릴 수 있다
```

이게 먼저 되어야 프론트 담당자도 백엔드 응답 형태에 맞춰 작업할 수 있습니다.

실행 확인은 아래 순서로 합니다.

```bash
cd backend
uv sync
uv run fastapi dev src/app.py
```

서버가 켜지면 브라우저에서 확인합니다.

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

`/docs`는 FastAPI가 자동으로 만들어주는 API 문서입니다. 백엔드 초보자는 이 화면을 자주 보면서 API 요청/응답을 확인하면 됩니다.

## 5. 단계별 구현 순서

### 1단계: `schemas/chat.py`에서 JSON 모양 먼저 정하기

프론트 문서에 이미 권장 응답 구조가 있습니다.

```json
{
  "summary": "...",
  "details": ["..."],
  "laws": [{"name": "...", "article": "..."}],
  "table": {"headers": ["..."], "rows": [["..."]]},
  "sources": ["..."],
  "warning": "..."
}
```

따라서 백엔드도 이 구조를 그대로 Pydantic 모델로 만들어야 합니다.

처음 만들 모델은 아래 정도면 됩니다.

- `ChatRequest`: 사용자가 보내는 질문
- `LawReference`: 관련 법령 이름과 조항
- `TableData`: 표 헤더와 행
- `ChatResponse`: 프론트가 받는 최종 응답

여기서 중요한 점은 "응답 구조를 먼저 고정"하는 것입니다. 그래야 Agent 내부가 바뀌어도 프론트는 덜 흔들립니다.

### 2단계: `api/chat.py`에 `/api/chat` 만들기

처음에는 LLM을 부르지 말고 mock 응답만 반환합니다.

예상 API 모양은 아래처럼 잡으면 됩니다.

```text
POST /api/chat

request:
{
  "question": "장애인 고용장려금 신청 조건이 뭐야?"
}

response:
{
  "summary": "...",
  "details": ["..."],
  "laws": [{"name": "...", "article": "..."}],
  "table": {"headers": ["..."], "rows": [["..."]]},
  "sources": ["..."],
  "warning": "..."
}
```

처음부터 정확한 답변이 아니어도 됩니다. 중요한 것은 프론트와 약속한 구조로 응답하는 것입니다.

### 3단계: `app.py`에서 chat 라우터 연결하기

`api/chat.py`에 API를 만들어도 `app.py`에서 연결하지 않으면 서버에 등록되지 않습니다.

`app.py`의 역할은 커질수록 단순해야 합니다.

- FastAPI 앱 생성
- CORS 설정
- 기본 health API
- `api/chat.py` 라우터 연결

`app.py` 안에 실제 상담 로직을 많이 넣지 않는 것이 좋습니다.

### 4단계: `prompt/system.md` 주제 맞추기

현재 system prompt는 "노인복지" 기준으로 되어 있습니다. 프로젝트 주제에 맞게 "장애인 및 취약계층 복지/법률 상담 Agent"로 바꿔야 합니다.

프롬프트에는 최소한 아래 원칙이 들어가면 좋습니다.

- 쉬운 말로 답한다.
- 법률/복지 정보는 출처가 있을 때만 단정한다.
- 최신성 확인이 필요한 내용은 확인 필요라고 말한다.
- 신청 방법, 자격 조건, 문의 기관을 분리해서 설명한다.
- 내부 추론 과정은 노출하지 않는다.
- 법률 자문이 아니라 정보 안내라는 점을 필요할 때 표시한다.

### 5단계: `prompt_loader.py`로 프롬프트 파일 읽기

프롬프트 문장을 코드 안에 직접 길게 쓰면 나중에 수정하기 어렵습니다.

따라서 `prompt/system.md`를 파일로 두고, `prompt_loader.py`에서 읽어오는 구조가 좋습니다.

처음 목표는 단순합니다.

```text
load_system_prompt()
-> backend/src/prompt/system.md 내용을 문자열로 반환
```

### 6단계: `openrouter_llm.py`에서 LLM 호출 담당하기

`settings.py`에는 이미 OpenRouter 관련 설정이 추가되어 있습니다.

- `openrouter_api_key`
- `openrouter_model`
- `openrouter_app_title`
- `openrouter_app_url`
- `llm_temperature`
- `llm_timeout_ms`
- `llm_max_retries`
- `llm_reasoning_effort`

그래서 LLM 호출 코드는 `openrouter_llm.py`로 분리하는 것이 좋습니다.

단, 이 단계는 mock API가 먼저 성공한 뒤에 해야 합니다. API 구조가 안 잡힌 상태에서 LLM부터 연결하면 어디서 문제가 났는지 찾기 어렵습니다.

### 7단계: `agent/graph.py`에서 Agent 흐름 만들기

나중에 LangGraph를 쓴다면 `graph.py`가 담당할 일은 이런 흐름입니다.

```text
사용자 질문
-> 질문 의도 파악
-> RAG 검색 필요 여부 판단
-> 관련 문서 검색
-> LLM 답변 생성
-> 출처/법령/표 데이터 정리
-> ChatResponse로 반환
```

처음부터 LangGraph를 완성하려고 하지 말고, 처음에는 일반 함수 하나로 시작해도 됩니다.

```text
run_agent(question: str) -> ChatResponse
```

이 함수가 mock 응답을 반환하다가, 나중에 RAG와 LLM을 연결하면 됩니다.

### 8단계: `logger.py`로 로그 남기기

백엔드에서는 print보다 logging을 쓰는 것이 좋습니다.

처음에는 아래 정보만 남겨도 충분합니다.

- 요청이 들어온 시간
- 질문 길이
- 응답 성공/실패
- 에러 메시지

주의: 사용자의 개인정보, API Key, 긴 상담 내용 전체를 무조건 로그에 남기면 안 됩니다.

### 9단계: 테스트 추가하기

처음 테스트는 어렵게 만들 필요 없습니다.

최소 테스트는 두 개면 됩니다.

- `/health`가 200을 반환하는지
- `/api/chat`이 정해진 JSON 필드를 반환하는지

이 테스트가 있으면 나중에 Agent 코드를 바꿔도 API 구조가 깨졌는지 바로 알 수 있습니다.

## 6. 파일별로 무엇을 물어보면 좋은지

앞으로 하나씩 물어볼 때는 이 순서가 좋습니다.

1. `backend/src/schemas/chat.py`  
   "이 파일에 어떤 Pydantic 모델을 만들어야 해?"

2. `backend/src/api/chat.py`  
   "이 파일에 `/api/chat` 엔드포인트를 어떻게 만들어?"

3. `backend/src/app.py`  
   "chat 라우터를 FastAPI 앱에 어떻게 연결해?"

4. `backend/src/prompt/system.md`  
   "우리 프로젝트 주제에 맞게 system prompt를 어떻게 고쳐?"

5. `backend/src/prompt/prompt_loader.py`  
   "md 프롬프트 파일을 Python에서 어떻게 읽어?"

6. `backend/src/agent/openrouter_llm.py`  
   "OpenRouter API를 호출하는 코드를 어떻게 분리해?"

7. `backend/src/agent/graph.py`  
   "Agent 실행 흐름을 어떤 함수부터 만들면 돼?"

8. `backend/src/logger.py`  
   "로그 설정은 어떻게 시작하면 돼?"

9. `backend/tests/test_chat.py`  
   "API 테스트는 어떻게 써?"

## 7. 지금 당장 하면 안 되는 것

초보 단계에서는 아래를 먼저 하지 않는 편이 좋습니다.

- 데이터베이스부터 붙이기
- 로그인/회원가입부터 만들기
- LangGraph 전체 구조를 처음부터 복잡하게 만들기
- RAG 검색 품질 튜닝부터 하기
- 응답을 Markdown 자유형 문자열로만 반환하기
- API Key를 코드에 직접 쓰기
- `.env` 파일을 Git에 올리기

이 프로젝트에서 지금 가장 중요한 것은 "백엔드 API 계약"입니다.

프론트가 기대하는 JSON 모양을 먼저 안정시키고, 그 다음에 내부 Agent 품질을 높이면 됩니다.

## 8. 백엔드 첫 번째 완성 기준

1차 완성 기준은 아래 정도로 잡으면 됩니다.

- `uv run fastapi dev src/app.py`로 서버가 켜진다.
- `/health`가 정상 응답한다.
- `/docs`에서 `/api/chat`이 보인다.
- `/api/chat`에 질문을 보내면 mock JSON 응답이 온다.
- 응답에는 `summary`, `details`, `laws`, `table`, `sources`, `warning` 필드가 있다.
- Streamlit mock UI의 응답 구조와 백엔드 응답 구조가 맞다.

여기까지 되면 백엔드 초반 구조는 성공입니다.

## 9. 추천 작업 순서 한 줄 요약

```text
실행 확인
-> schema 정의
-> mock chat API
-> app.py 라우터 연결
-> 프론트와 응답 구조 확인
-> prompt 정리
-> LLM 호출 분리
-> Agent 흐름 연결
-> RAG 검색 연결
-> 테스트 추가
```

초보 백엔드 담당자는 `schemas/chat.py`부터 시작하는 것이 가장 좋습니다. 백엔드는 결국 "어떤 요청을 받고 어떤 응답을 줄지"를 정확히 정하는 일이기 때문입니다.
