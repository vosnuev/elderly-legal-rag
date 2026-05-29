# Streamlit Frontend Design

## 1. 응답 JSON 스키마

프론트는 LLM 또는 백엔드에서 자유형 markdown이 아니라 구조화된 JSON을 받아야 합니다.

```json
{
  "summary": "...",
  "details": ["..."],
  "laws": [
    {"name": "...", "article": "..."}
  ],
  "table": {
    "headers": ["..."],
    "rows": [["...", "..."]]
  },
  "sources": ["..."],
  "warning": "..."
}
```

### 필드 설명

- `summary`: 사용자에게 보여줄 핵심 요약
- `details`: 상세 설명을 리스트 형태로 제공
- `laws`: 관련 법령 및 조항 정보를 카드 형태로 렌더링
- `table`: 질문이 수치, 표 형태일 때 자동 테이블 렌더링
- `sources`: citation / 출처 목록
- `warning`: 경고 메시지나 fallback 안내

## 2. Streamlit UI / 렌더링 설계

### 상담 진입 흐름

- 첫 화면에서는 태어난 연도, 사는 지역, 기타 정보 등 기본정보만 입력받습니다.
- 기본정보가 완료되기 전에는 질문 입력창과 예시 상담을 노출하지 않습니다.
- 상담 시작 후 사용자 질문에는 기본정보 컨텍스트를 자동으로 붙여 백엔드 프롬프트에 전달합니다.
- 모호한 질문은 의도 선택 버튼 대신 assistant가 채팅 메시지로 필요한 정보 범위를 되묻습니다.

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

## 3. mock response 기반 프론트 코드

현재 `streamlit/src/views/mock_ui.py`는 다음 구조로 동작합니다.

- `MOCK_RESPONSE`에 구조화된 JSON 데이터 저장
- `st.info`로 요약 표시
- `st.expander`로 상세 내용 표시
- `st.dataframe`으로 테이블 자동 렌더링
- 관련 법 조항은 `st.markdown`으로 카드 형태 렌더링
- 출처 목록과 경고 메시지를 별도 섹션으로 구성

## 4. 작업 가이드

1. 먼저 백엔드와 응답 스키마를 합의합니다.
2. 프론트는 `MOCK_RESPONSE` 형태를 기준으로 렌더링 구현합니다.
3. 실제 API가 준비되면 `get_mock_response`를 백엔드 호출로 대체합니다.
4. citation은 별도 패널로 분리하고, `st.expander`/`st.tabs`로 긴 답변을 숨깁니다.

## 5. 백엔드 연결 전환 구조

프론트는 DB나 AI API key를 직접 사용하지 않고 백엔드 API만 호출합니다.

- `src/shared/backend.py`: `STREAMLIT_BACKEND_BASE_URL` 기준으로 `/api/chat` payload 구성 및 호출
- `src/api_client.py`: 백엔드 HTTP 요청을 실행하는 저수준 클라이언트
- `src/response_renderer.py`: 백엔드 `ChatResponse`를 공통 렌더링
- `STREAMLIT_USE_BACKEND_API=false`: 임시 데이터 기반 UI 개발
- `STREAMLIT_USE_BACKEND_API=true`: 백엔드 API 연결 모드

프론트에서 직접 관리하는 환경 변수는 화면 설정과 백엔드 주소입니다. AI API key, DB URL, RAG 연결 정보는 `backend/.env`에서 관리합니다.

## 6. 실행 방법

```bash
cd streamlit
uv sync
uv run streamlit run streamlit.py
```
