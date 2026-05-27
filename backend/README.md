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

## Current Backend Work

현재 backend에는 채팅 API 외에 문서 업로드에서 RAG 적재 요청까지 이어지는 API 초안이 추가되어 있습니다.

- `POST /api/files/upload`로 사용자가 올린 파일을 backend 로컬 저장소에 저장합니다.
- 저장된 파일 정보와 `job_id`를 RAG 서버의 `POST /ingest`로 전달합니다.
- `GET /api/files/{job_id}/status`로 RAG 서버의 ingest 상태를 조회합니다.
- 파일 처리 단계 응답은 `uploaded`, `parsed`, `converted`, `stored`, `indexed`, `failed`를 기준으로 표현합니다.
- 현재 즉시 처리 가능한 입력 범위는 RAG 서버 기준 `.csv`, `.json`, `.py`, `.txt`, `.md`입니다.
- PDF, DOCX, HWP 등 실제 문서 파싱은 후속 RAG 파서/로더 구현 범위입니다.
- `POST /api/chat` 응답에 프론트 결과 화면이 사용할 `sources`, `references`, `eligibility`, `confidence`, `evidence_status` 계약을 추가했습니다.
- RAG 검색 실패, 근거 문서 없음, LLM fallback 상태를 `evidence_status`로 구분합니다.

## Runtime

- Python 3.13
- FastAPI
- LangChain
- LangGraph
- langchain-openai
- Pydantic / pydantic-settings
- OpenRouter 호환 Chat Completions API
- python-multipart

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
    ├── file_store.py             # 업로드 파일 로컬 저장
    ├── rag_ingest_client.py      # RAG ingest/status API 호출
    ├── api/
    │   ├── chat.py               # POST /api/chat
    │   └── files.py              # POST /api/files/upload, GET /api/files/{job_id}/status
    ├── prompt/
    │   ├── __init__.py           # graph.py가 사용하는 prompt 함수 export
    │   ├── templates.py          # ChatPromptTemplate 생성 함수
    │   ├── prompt_loader.py      # markdown prompt 로더
    │   ├── clarification_*.md    # 보기 생성 prompt
    │   └── grounded_answer_*.md  # RAG 기반 답변 생성 prompt
    ├── schemas/
    │   ├── chat.py               # 채팅 요청/응답 Pydantic schema
    │   └── files.py              # 파일 업로드/ingest 상태 Pydantic schema
    └── agent/
        ├── graph.py              # 보기 생성, RAG 검색 호출, LLM 답변 생성
        └── openrouter_llm.py     # OpenRouter ChatOpenAI client 생성
```

## File Upload And Ingest Flow

```text
Frontend
-> backend POST /api/files/upload
-> backend/storage/uploads/{job_id}/{file_name} 저장
-> RAG POST /ingest 호출
-> RAG가 파싱/변환/적재/인덱싱 상태 관리
-> frontend가 backend GET /api/files/{job_id}/status로 상태 확인
```

backend는 원본 파일 저장과 RAG 서버 호출을 담당합니다. 실제 파싱, 변환, RAG input 적재, 인덱싱 완료 여부 판단은 RAG 서버 책임입니다.

현재 upload API는 RAG ingest 요청이 성공적으로 접수되면 `parsed` 단계를 `pending`으로 반환합니다. 최종 `indexed` 완료 여부는 status API로 다시 조회합니다.

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
| `BACKEND_UPLOAD_DIR` | `backend/storage/uploads` | backend 업로드 파일 저장 위치 |
| `BACKEND_RAG_INGEST_URL` | `http://127.0.0.1:8010/ingest` | RAG 파일 ingest 요청 API |
| `BACKEND_RAG_INGEST_STATUS_URL` | `http://127.0.0.1:8010/ingest/status` | RAG 파일 ingest 상태 조회 API prefix |
| `BACKEND_RAG_INGEST_TIMEOUT_MS` | `10000` | RAG ingest 요청 timeout |
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
BACKEND_RAG_INGEST_URL=http://127.0.0.1:8011/ingest \
BACKEND_RAG_INGEST_STATUS_URL=http://127.0.0.1:8011/ingest/status \
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

### `POST /api/files/upload`

사용자가 업로드한 파일을 backend 로컬 저장소에 저장하고 RAG 서버에 파싱/적재를 요청합니다.

요청 형식은 `multipart/form-data`이며 필드명은 `file`입니다.

```bash
curl -s http://127.0.0.1:8001/api/files/upload \
  -F "file=@./sample.md"
```

응답 예시:

```json
{
  "job_id": "0f1e2d3c4b5a...",
  "file_name": "sample.md",
  "content_type": "text/markdown",
  "file_size": 1234,
  "current_stage": "uploaded",
  "completed": false,
  "stages": [
    {
      "stage": "uploaded",
      "status": "success",
      "message": "파일 업로드가 완료되었습니다.",
      "path": "backend/storage/uploads/{job_id}/sample.md"
    },
    {
      "stage": "parsed",
      "status": "pending",
      "message": "RAG 서버에 파싱/변환/적재/인덱싱 작업을 요청했습니다."
    }
  ],
  "warning": null
}
```

응답 주요 필드:

| 필드 | 설명 |
| --- | --- |
| `job_id` | 업로드/ingest 상태 조회용 작업 ID |
| `file_name` | 업로드된 원본 파일명 |
| `content_type` | 업로드 MIME type |
| `file_size` | 파일 크기 |
| `current_stage` | 현재 처리 단계 |
| `completed` | 전체 처리 완료 여부 |
| `stages` | 단계별 성공/대기/실패 상세 |
| `warning` | RAG ingest 요청 실패 등 확인 필요 메시지 |

현재 backend는 파일 확장자별 파싱을 직접 수행하지 않습니다. RAG 서버가 지원하지 않는 파일 형식은 status 응답에서 `failed`로 확인합니다.

### `GET /api/files/{job_id}/status`

RAG 서버에서 파일 ingest 상태를 조회합니다.

```bash
curl -s http://127.0.0.1:8001/api/files/{job_id}/status
```

응답 예시:

```json
{
  "job_id": "0f1e2d3c4b5a...",
  "file_name": "sample.md",
  "current_stage": "indexed",
  "completed": true,
  "stages": [
    { "stage": "uploaded", "status": "success", "message": "backend 업로드 파일 경로를 수신했습니다." },
    { "stage": "parsed", "status": "success", "message": "파일 형식과 경로 검증이 완료되었습니다." },
    { "stage": "converted", "status": "success", "message": "현재 검색 엔진에서 읽을 수 있는 원본 형식으로 확인되었습니다." },
    { "stage": "stored", "status": "success", "message": "RAG input 디렉터리에 파일을 적재했습니다." },
    { "stage": "indexed", "status": "success", "message": "검색 로더가 다음 요청부터 해당 파일을 읽을 수 있습니다." }
  ],
  "warning": null
}
```

RAG 서버 연결 실패, timeout, HTTP 오류가 발생하면 backend는 `current_stage: "failed"`와 `warning`을 포함한 응답을 반환합니다.

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
| `laws` | 관련 법령명과 조항 |
| `table` | 프론트에서 표로 렌더링할 구조화 데이터 |
| `options` | 질문 범위를 좁히기 위한 보기 3개 |
| `allow_custom_input` | 기타 직접 입력 허용 여부 |
| `sources` | 간단 출처 문자열 |
| `references` | 파일명, URL, section, excerpt, score를 포함한 상세 출처 |
| `eligibility` | 자격 가능성 판단 상태, 이유, 추가 필요 정보 |
| `confidence` | 답변 신뢰도. 0~1 범위 |
| `evidence_status` | 근거 충분 여부 또는 fallback 상태 |
| `warning` | 확인 필요 또는 fallback 안내 |

### Frontend Result Contract

프론트 결과 화면은 `/api/chat` 응답의 구조화 필드를 기준으로 렌더링합니다.

| 필드 | 화면 사용처 |
| --- | --- |
| `summary` | 답변 상단 요약 |
| `details` | 상세 설명 목록 |
| `laws` | 관련 법 조항 카드 |
| `table` | 비교/절차/조건 표 |
| `sources` | 간단 출처 목록 |
| `references` | 상세 출처, 원문 발췌, 링크, 검색 점수 |
| `eligibility` | 자격 가능성 또는 추가 확인 필요 안내 |
| `confidence` | 신뢰도 표시 |
| `evidence_status` | 근거 충분/부족/fallback 상태 표시 |
| `warning` | 사용자에게 보여줄 주의 메시지 |

`evidence_status` 값:

| 값 | 의미 |
| --- | --- |
| `sufficient` | RAG 근거와 LLM 답변이 정상 생성됨 |
| `insufficient` | 검색 결과가 없거나 입력 조건이 부족해 단정할 수 없음 |
| `rag_error` | RAG 검색 서버 연결, timeout, 응답 형식 오류 |
| `llm_fallback` | 문서는 찾았지만 LLM 답변 생성 실패로 검색 결과를 그대로 반환 |

프론트 연결용 mock response:

```json
{
  "session_id": "demo-session-id",
  "kind": "answer",
  "question_type": "search",
  "summary": "근거에서 확인된 범위에서는 수원시 노인일자리 신청은 모집 공고 확인 후 수행기관에 신청하는 방식입니다.",
  "details": [
    "신청 전 모집 대상, 기간, 수행기관을 확인해야 합니다. [1]",
    "문의처는 공고에 표시된 담당부서 또는 수행기관 기준으로 안내해야 합니다. [1]"
  ],
  "laws": [],
  "table": null,
  "sources": [
    "수원시 노인일자리 안내 / senior_jobs.md / 신청방법 / score=0.87"
  ],
  "references": [
    {
      "title": "수원시 노인일자리 안내",
      "file_name": "senior_jobs.md",
      "url": "https://example.com/suwon-senior-jobs",
      "page": null,
      "article": null,
      "section": "신청방법",
      "excerpt": "노인일자리 신청은 모집 기간 내 수행기관 또는 담당부서를 통해 접수합니다.",
      "score": 0.87
    }
  ],
  "eligibility": {
    "status": "confirmation_required",
    "reason": "나이와 거주지는 확인됐지만 모집 유형별 세부 조건은 추가 확인이 필요합니다.",
    "required_info": ["참여 희망 사업 유형", "모집 공고 기준 신청 기간"]
  },
  "confidence": 0.78,
  "evidence_status": "sufficient",
  "options": [],
  "allow_custom_input": false,
  "warning": null
}
```

## Conversation Flow

### Chat

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

### File Upload

```text
1. 사용자가 파일을 `POST /api/files/upload`로 보냄
2. backend가 파일명을 basename으로 정리하고 `upload_dir/{job_id}/{file_name}`에 저장
3. backend가 `RagIngestRequest`를 만들어 RAG `POST /ingest` 호출
4. RAG 요청 접수 성공 시 backend가 업로드 성공과 ingest pending 상태를 반환
5. 사용자가 `GET /api/files/{job_id}/status`로 처리 상태 조회
6. RAG가 `indexed`를 반환하면 다음 검색 요청부터 해당 파일이 검색 대상에 포함됨
```

현재 backend 저장소는 로컬 파일 시스템 기반입니다. 운영 단계에서는 업로드 파일 보존 정책, 파일 크기 제한, 악성 파일 검사, 사용자 권한 확인, object storage 연동 여부를 별도로 정해야 합니다.

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

파일 업로드와 RAG ingest 연결 확인:

```bash
curl -s http://127.0.0.1:8001/api/files/upload \
  -F "file=@./sample.md"
```

응답의 `job_id`로 상태 조회:

```bash
curl -s http://127.0.0.1:8001/api/files/{job_id}/status
```

채팅 응답 schema와 근거 상태 값 확인:

```bash
cd backend
PYTHONPATH=src uv run python - <<'PY'
from schemas.chat import ChatResponse, EvidenceStatus, SourceReference

print(ChatResponse(summary="ok").model_dump(mode="json"))
print(ChatResponse(summary="fail", confidence=0.0, evidence_status=EvidenceStatus.RAG_ERROR).model_dump(mode="json"))
print(SourceReference(title="doc", score=0.87).model_dump(mode="json"))
PY
```

## Notes

- 프롬프트를 수정 시, `src/prompt/*.md`만 수정하면 됩니다.
- 프롬프트 파일 구성이나 LangChain template 생성 방식 변동 시, `src/prompt/templates.py`만 수정하면 됩니다.
- LLM 답변 생성이 실패하면 검색 결과와 출처를 fallback으로 반환합니다.
- LLM 답변 생성이 실패하면 `evidence_status: "llm_fallback"`로 응답합니다.
- RAG 검색 결과가 없으면 정책 내용을 단정하지 않고 `evidence_status: "insufficient"`로 응답합니다.
- RAG 검색 서버 오류가 있으면 `evidence_status: "rag_error"`로 응답합니다.
- `manual_chat.py`의 표시는 프론트엔드가 없는 상황에서 하는 수동 테스트용입니다.
- 파일 업로드 API는 backend 기준 초안입니다. PDF 같은 실제 문서 파싱 품질은 RAG 파서 구현과 함께 별도 검증해야 합니다.
