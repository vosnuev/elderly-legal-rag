# Streamlit

Streamlit 기반 법률 RAG 프론트엔드 작업 공간입니다.

## Runtime

- Python 3.13
- Streamlit
- Pydantic / pydantic-settings
- Pandas

## Layout

```text
streamlit/
├── streamlit.py        # `streamlit run` 실행 진입점
├── src/
│   ├── app.py          # Streamlit 앱 부트스트랩
│   ├── navigation.py   # 사이드바와 페이지 라우팅
│   ├── settings.py     # Streamlit 설정 단일 로딩 지점
│   ├── chat_backend_client.py # backend /chat 또는 mock stream 클라이언트
│   ├── response_renderer.py # backend ChatResponse 공통 렌더러
│   ├── pages/          # 실제 사용자 페이지 진입점
│   ├── components/     # 채팅 패널, 입력 요약, 페이지 hero 등 재사용 UI
│   ├── forms/          # 상담 form, 선택지, prompt context 문서
│   ├── services/       # 채팅 흐름, 위치 변환 등 화면 밖 로직
│   ├── styles/         # Streamlit CSS
│   └── data/           # 임시 법령 데이터
├── frontend_design.md
├── frontend_usecases.md
├── pyproject.toml
└── uv.lock
```

## Toolchain

이 디렉토리는 `uv`를 사용합니다.

```bash
uv sync
uv run streamlit run streamlit.py
```

의존성 추가는 이 디렉토리 안에서 실행합니다.

```bash
uv add <package>
```

## 페이지 구성

- `streamlit.py`: Streamlit 실행 진입점
- `src/app.py`: Streamlit 앱 부트스트랩
- `src/navigation.py`: 사이드바, 페이지 목록, 선택된 페이지 렌더링
- `src/chat_backend_client.py`: backend `/chat` 호출과 mock stream generator
- `src/response_renderer.py`: backend `ChatResponse`를 Streamlit 컴포넌트로 렌더링
- `src/pages/consulting_page.py`: 상담 form 입력 후 채팅형 상담으로 넘어가는 페이지
- `src/pages/law_record_page.py`: 주요 법령을 분야별로 정리해서 보여주는 페이지
- `src/components/`: 입력정보 요약, 채팅 패널, 페이지 hero
- `src/forms/`: 상담 form 선택지, 첫 턴 context 구성, form 업데이트 문서
- `src/services/chat_flow.py`: 상담 질문 제출, session_id 유지, backend/mock stream 처리
- `src/services/geolocation.py`: 현재 위치를 지역 문자열로 변환하는 역지오코딩
- `src/styles/app.css`: Streamlit 전역 CSS
- `src/data/legal_data.py`: 검색 화면과 법령 정리 화면에서 사용하는 임시 법령 데이터

## Backend Chat 응답 스키마

현재 Streamlit은 backend `/chat` 응답을 기준으로 렌더링합니다.

```json
{
  "answer": "...",
  "tool_calls": [],
  "sources": []
}
```

## 프론트 UI 설계 요약

- 첫 화면 상담 form 입력 → 상담 시작 후 채팅형 질문/답변으로 진행
- 첫 질문에는 form context를 함께 보내고, 이후 turn은 같은 `session_id`로 사용자 입력만 전송
- backend memory 연결은 backend가 `session_id`를 LangGraph/LangChain `thread_id`로 매핑해서 처리
- Streamlit 컴포넌트로 안정적으로 표시
  - `st.dataframe`, `st.expander`, `st.info`, `st.warning`, `st.chat_message`
- citation / 출처는 별도 패널로 분리
- 긴 답변은 `st.expander` 또는 `st.tabs`로 접기

## Mock Stream 기반 테스트

`STREAMLIT_CHAT_BACKEND_MOCK=true`이면 `src/chat_backend_client.py`가 backend agent streaming 응답을 흉내낸 generator를 사용합니다. 이 모드에서 backend 서버 없이도 form, session_id 유지, 채팅 렌더링 흐름을 확인할 수 있습니다.

## 추가 문서

- `frontend_design.md`: 프론트 설계 가이드 문서
- `frontend_usecases.md`: 사용자 유스케이스와 렌더링 화면 요소 매핑 문서

## Environment

- 예시 파일: `.env.example`
- 실제 로컬 환경 파일: `.env` (커밋 금지)
- 환경 변수는 `STREAMLIT_` prefix를 사용하며 `src/settings.py`에서 pydantic-settings로 로딩합니다.
- `STREAMLIT_BACKEND_BASE_URL`: 백엔드 API 서버 주소
- `STREAMLIT_CHAT_BACKEND_MOCK=true`: mock stream generator 사용
- `STREAMLIT_CHAT_BACKEND_MOCK=false`: backend `/chat` 호출
- `STREAMLIT_CHAT_MOCK_CHUNK_DELAY_SECONDS`: mock stream chunk delay
- `STREAMLIT_LOG_LLM_CONTEXT=true`: frontend가 backend로 보낼 `message` 본문을 로그로 출력

AI API key, DB URL, RAG 연결 정보는 프론트가 아니라 `backend/.env`에서 관리합니다.
