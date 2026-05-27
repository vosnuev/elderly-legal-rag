# Backend

FastAPI 기반 메인 백엔드 서비스입니다. 
사용자의 질문을 받고, 보기 선택/기타 입력/후속 질문 흐름을 관리한 뒤 RAG 검색 결과를 LLM에 전달해 사용자에게 보여줄 구조화 응답을 생성합니다.

## 역할

```text
사용자 또는 프론트엔드
-> backend /api/chat
-> 세션/사용자 정보/이전 대화 반영
-> RAG 검색 서버 /search 호출
-> 검색 결과와 출처를 LLM에 전달
-> summary/details/references 형태로 응답
```

백엔드는 사용자-facing API를 담당하고, RAG 서버는 문서 검색만 담당합니다. 
프론트엔드는 `rag/`를 직접 호출하지 않고 `backend /api/chat`만 호출하는 구조를 기준으로 합니다.

## Runtime

- Python 3.13
- FastAPI
- LangChain
- LangGraph
- langchain-openai
- Pydantic / pydantic-settings
- OpenRouter 호환 Chat Completions API

## Directory Layout

```text
backend/
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── scripts/
│   └── manual_chat.py            # 터미널 수동 대화 테스트 도구
└── src/
    ├── app.py                    # FastAPI 앱 생성, health, router 연결
    ├── settings.py               # BACKEND_ 환경 변수 로딩
    ├── logger.py                 # 공통 logging 설정
    ├── session_store.py          # 메모리 기반 session/user profile/history 저장
    ├── api/
    │   └── chat.py               # POST /api/chat
    ├── prompt/
    │   ├── __init__.py           # graph.py가 사용하는 prompt 함수 export
    │   ├── templates.py          # ChatPromptTemplate 생성 함수
    │   ├── prompt_loader.py      # markdown prompt 로더
    │   ├── clarification_*.md    # 보기 생성 prompt
    │   └── grounded_answer_*.md  # RAG 기반 답변 생성 prompt
    ├── schemas/
    │   └── chat.py               # 요청/응답 Pydantic schema
    └── agent/
        ├── graph.py              # 보기 생성, RAG 검색 호출, LLM 답변 생성
        └── openrouter_llm.py     # OpenRouter ChatOpenAI client 생성
```

프롬프트 본문은 `src/prompt/*.md`에 분리되어 있습니다. `graph.py`에는 프롬프트 파일 이름을 직접 적지 않고, `create_clarification_prompt()`, `create_grounded_answer_prompt()` 등 프롬프트를 만들어주는 함수만 호출합니다.

## Prompt Structure

`prompt_loader.py`가 markdown을 문자열로 읽고, `templates.py`가 그 문자열을 LangChain `ChatPromptTemplate`로 감싸서 함수처럼 호출할 수 있게 만든 구조입니다.

```text
src/prompt/*.md
-> src/prompt/prompt_loader.py 의 load_prompt()
-> src/prompt/templates.py 의 create_*_prompt()
-> src/agent/graph.py 의 generate_* 함수
```

연결 관계:

| Prompt 파일 | 함수 | 사용 위치 |
| --- | --- | --- |
| `src/prompt/clarification_system.md` | `create_clarification_prompt()` | `agent/graph.py`의 `generate_clarification_options()` |
| `src/prompt/clarification_human.md` | `create_clarification_prompt()` | `agent/graph.py`의 `generate_clarification_options()` |
| `src/prompt/grounded_answer_system.md` | `create_grounded_answer_prompt()` | `agent/graph.py`의 `generate_grounded_answer()` |
| `src/prompt/grounded_answer_human.md` | `create_grounded_answer_prompt()` | `agent/graph.py`의 `generate_grounded_answer()` |

코드에서는 이렇게 사용합니다.

```python
from prompt import create_grounded_answer_prompt

prompt = create_grounded_answer_prompt()
```

## Environment

실제 환경 변수는 `backend/.env`에 둡니다. `.env`는 커밋하지 않습니다.

예시 파일:

```bash
cp .env.example .env
```

주요 설정:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `BACKEND_API_HOST` | `127.0.0.1` | backend 실행 host |
| `BACKEND_API_PORT` | `8000` | backend 실행 port |
| `BACKEND_OPENROUTER_API_KEY` | 없음 | OpenRouter API key |
| `BACKEND_OPENROUTER_MODEL` | `openai/gpt-oss-120b` | 답변 생성 모델 |
| `BACKEND_RAG_SEARCH_URL` | `http://127.0.0.1:8010/search` | RAG 검색 API |
| `BACKEND_RAG_SEARCH_TOP_K` | `5` | 검색 결과 개수 |
| `BACKEND_RAG_SEARCH_TIMEOUT_MS` | `10000` | RAG 검색 timeout |
| `BACKEND_LOG_LEVEL` | `INFO` | 로그 레벨 |

## Install

이 디렉토리는 `uv`를 사용합니다.

```bash
cd backend
uv sync
```

의존성 추가:

```bash
uv add <package>
```

## Run

RAG 서버가 먼저 실행 중이어야 답변 검색이 가능합니다.

```bash
cd rag
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8011
```

backend 실행:

```bash
cd backend

BACKEND_RAG_SEARCH_URL=http://127.0.0.1:8011/search \
BACKEND_RAG_SEARCH_TOP_K=3 \
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8001
```

상태 확인:

```bash
curl -s http://127.0.0.1:8001/health
```

## API

### `GET /health`

서비스 상태 확인용 endpoint입니다.

### `GET /api/system/dependencies`

백엔드 런타임과 주요 stack 정보를 반환합니다.

### `POST /api/chat`

사용자 질문, 사용자 정보, 보기 선택, 기타 입력, 후속 질문을 처리하는 메인 endpoint입니다.

최초 질문 예시:

```json
{
  "question": "수원시 노인일자리 신청방법이 궁금해요",
  "user_profile": {
    "age": 72,
    "location": {
      "city": "경기도",
      "district": "수원시"
    },
    "monthly_income_krw": 700000,
    "household_size": 1
  }
}
```

보기 선택 예시:

```json
{
  "session_id": "처음 응답에서 받은 session_id",
  "question": "수원시 노인일자리 신청방법이 궁금해요",
  "selected_option": {
    "id": "1",
    "title": "신청 절차",
    "search_focus": "수원시 노인일자리 신청 절차와 방법"
  }
}
```

기타 입력 예시:

```json
{
  "session_id": "처음 응답에서 받은 session_id",
  "question": "수원시 노인일자리 신청방법이 궁금해요",
  "custom_intent": "담당부서 문의처 중심으로 찾아줘"
}
```

후속 질문 예시:

```json
{
  "session_id": "처음 응답에서 받은 session_id",
  "question": "그럼 어디에 문의하면 돼?",
  "is_follow_up": true
}
```

응답 주요 필드:

| 필드 | 설명 |
| --- | --- |
| `session_id` | 후속 요청에서 이어 쓰는 세션 ID |
| `kind` | `clarification` 또는 `answer` |
| `question_type` | `search`, `custom_intent`, `follow_up` 등 |
| `summary` | 사용자에게 보여줄 핵심 답변 |
| `details` | 상세 설명 목록 |
| `options` | 질문 범위를 좁히기 위한 보기 3개 |
| `allow_custom_input` | 기타 직접 입력 허용 여부 |
| `sources` | 간단 출처 문자열 |
| `references` | 파일명, URL, section, excerpt를 포함한 상세 출처 |
| `warning` | 확인 필요 또는 fallback 안내 |

## Conversation Flow

```text
1. 사용자가 기본 정보와 질문을 보냄
2. backend가 보기 3개와 기타 입력 가능 여부를 응답
3. 사용자가 보기 1/2/3 또는 기타 입력을 보냄
4. backend가 원 질문 + 선택/기타 의도 + 필요한 사용자 정보를 RAG query로 구성
5. backend가 RAG 검색 결과를 받음
6. backend가 검색 결과와 출처를 LLM에 전달
7. backend가 최종 답변과 references를 응답
8. 사용자가 후속 질문을 보내면 session history를 반영
```

사용자 정보는 항상 검색어에 넣지 않습니다. 지역은 지역/거주/지자체 관련 의도가 있을 때만 사용하고, 나이/소득은 자격/조건/대상/소득 관련 질문일 때만 보조 조건으로 사용합니다.

## Session

`src/session_store.py`는 메모리 기반 세션 저장소입니다.

저장하는 값:

- `session_id`
- `user_profile`
- 최근 대화 turn
- 사용자가 선택한 보기
- 기타 입력 의도

주의:

- 서버를 재시작하면 세션이 사라집니다.
- 로컬 데모와 개발 검증용입니다.
- 배포 단계에서는 Redis 또는 DB 기반 저장소로 교체하는 것이 좋습니다.

## Manual Terminal Test

프론트엔드 없이 터미널에서 사용자처럼 직접 테스트할 수 있습니다.

```bash
cd backend

uv run python scripts/manual_chat.py \
  --base-url http://127.0.0.1:8001
```

지원 기능:

- 사용자 정보 입력
- 월소득 `100,000원` 형식 입력
- 월소득 한글 금액 표시
- 질문 입력
- 보기 1/2/3 선택
- 기타 직접 입력
- 후속 질문
- 이전 보기로 돌아가기
- 어느 입력 위치에서든 `q`, `/q`, `quit`, `exit`로 종료
- 출처와 근거 표시
- backend 연결 실패/validation 오류 안내

출력 속도를 끄고 싶으면:

```bash
uv run python scripts/manual_chat.py \
  --base-url http://127.0.0.1:8001 \
  --stream-delay 0
```

## Validation

문법/컴파일 확인:

```bash
cd backend
uv run python -m compileall src scripts
```

기본 API 확인:

```bash
curl -s http://127.0.0.1:8001/health
```

채팅 확인:

```bash
curl -s http://127.0.0.1:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "수원시 노인일자리 신청방법이 궁금해요",
    "user_profile": {
      "age": 72,
      "location": {
        "city": "경기도",
        "district": "수원시"
      }
    }
  }'
```

## Notes

- 프롬프트를 수정 시, `src/prompt/*.md`만 수정하면 됩니다.
- 프롬프트 파일 구성이나 LangChain template 생성 방식 변동 시, `src/prompt/templates.py`만 수정하면 됩니다.
- LLM 답변 생성이 실패하면 검색 결과와 출처를 fallback으로 반환합니다.
- RAG 검색 결과가 없으면 정책 내용을 단정하지 않고 `확인 필요`로 응답합니다.
- `manual_chat.py`의 표시는 프론트엔드가 없는 상황에서 하는 수동 테스트용입니다.
