# Streamlit Frontend Design

## 1. Backend Chat 응답 스키마

v1 Streamlit은 backend main agent의 `/chat` 응답을 기준으로 합니다. agent의 자연어 답변은 `answer`로 받고, tool 호출과 출처는 선택적으로 렌더링합니다.

```json
{
  "answer": "...",
  "tool_calls": [],
  "sources": []
}
```

### 필드 설명

- `answer`: 사용자에게 보여줄 최종 상담 답변
- `tool_calls`: agent가 호출한 tool 요약
- `sources`: RAG 또는 외부 문서 출처 목록

## 2. Streamlit UI / 렌더링 설계

### 상담 진입 흐름

- 첫 화면에서는 태어난 연도, 사는 지역, 상담 대상, 필요한 정보, 진행 단계, 기타 정보를 입력받습니다.
- 기본정보가 완료되기 전에는 질문 입력창과 예시 상담을 노출하지 않습니다.
- 첫 질문에는 form context를 자동으로 붙여 backend `/chat`의 `message`로 전달합니다.
- 이후 질문은 같은 `session_id`와 새 사용자 입력만 전달합니다.
- backend가 LangChain/LangGraph memory를 붙이면 `session_id`를 `thread_id`로 사용해 이전 context를 복원합니다.
- 모호한 질문은 backend agent가 채팅 답변 안에서 bullet 또는 table 형태로 되묻습니다.
- 선택지에 맞는 값이 없으면 `여기에 없어요`를 선택해 pass할 수 있습니다.
- `STREAMLIT_LOG_LLM_CONTEXT=true`일 때 frontend가 구성한 backend `message`를 structured log로 확인합니다.

### 페이지 구조

- `내 상황 상담`: 기본정보를 먼저 입력한 뒤 채팅형 상담을 진행
- `Use Cases`: 프론트엔드 유스케이스와 화면 요소 매핑
- `JSON Schema`: 응답 계약 및 스키마 설명
- `Mock Response UI`: mock 데이터를 이용한 렌더링 검증
- `LLM Parsing Test`: LLM 출력 형식별 파싱 검증
- `Design Notes`: 질문 유형별 렌더링 가이드

### 추천 컴포넌트

- `st.sidebar.radio`: 페이지 네비게이션
- `st.dataframe`: 표 렌더링
- `st.expander`: 긴 답변 접기/펼치기
- `st.info`, `st.warning`: 요약/경고 강조
- `st.chat_message`: 질문/응답 채팅 스타일
- `st.tabs`: JSON, 출처, 추가 설명 분리

### 렌더링 매핑

| 사용자 질문 유형 | 추천 렌더링 |
| --- | --- |
| "몇 %야?" | 표(`st.dataframe`) |
| "절차 알려줘" | 단계 리스트(`st.expander`) |
| "무슨 법 적용돼?" | 법 조항 카드(`st.markdown`) |
| "조건 뭐야?" | 체크리스트(`st.markdown`) |
| "신청 어디서 해?" | 링크/버튼 |

유스케이스별 화면 요소 매핑은 `frontend_usecases.md`와 Streamlit `Use Cases` 페이지에서 관리합니다.

## 3. mock stream 기반 프론트 코드

현재 `streamlit/src/chat_backend_client.py`는 `.env`의 `STREAMLIT_CHAT_BACKEND_MOCK` 값으로 mock/real backend를 전환합니다.

- `true`: backend 없이 agent stream 응답을 흉내낸 generator 사용
- `false`: `STREAMLIT_BACKEND_BASE_URL`의 `/chat` endpoint 호출
- 두 모드는 모두 `answer`, `tool_calls`, `sources` shape으로 렌더링

## 4. 작업 가이드

1. form 필드 수정은 `streamlit/src/forms/FORM_INSTRUCTIONS.md`를 먼저 확인합니다.
2. frontend DTO를 늘리지 말고 form 값은 첫 턴 context 문장으로 합성합니다.
3. backend 호출 payload는 `{session_id, message, metadata}`를 유지합니다.
4. citation은 별도 패널로 분리하고, `st.expander`/`st.tabs`로 긴 답변을 숨깁니다.

## 5. 백엔드 연결 전환 구조

프론트는 DB나 AI API key를 직접 사용하지 않고 백엔드 API만 호출합니다.

- `src/chat_backend_client.py`: `STREAMLIT_BACKEND_BASE_URL` 기준으로 `/chat` payload 구성 및 호출
- `src/services/chat_flow.py`: session_id 유지, 첫 턴 context seed, stream event 처리
- `src/forms/`: form 선택지와 context construction 규칙 관리
- `src/response_renderer.py`: 백엔드 `ChatResponse`를 공통 렌더링
- `STREAMLIT_CHAT_BACKEND_MOCK=true`: mock stream generator 사용
- `STREAMLIT_CHAT_BACKEND_MOCK=false`: backend `/chat` 연결 모드

프론트에서 직접 관리하는 환경 변수는 화면 설정과 백엔드 주소입니다. AI API key, DB URL, RAG 연결 정보는 `backend/.env`에서 관리합니다.

## 6. 실행 방법

```bash
cd streamlit
uv sync
uv run streamlit run streamlit.py
```
