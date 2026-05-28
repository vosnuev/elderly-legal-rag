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
│   ├── api_client.py   # 백엔드 /api/chat 호출 클라이언트
│   ├── response_renderer.py # 백엔드 ChatResponse 공통 렌더러
│   ├── pages/          # 실제 사용자 페이지 진입점
│   ├── components/     # 버튼, 프로필 폼, 채팅 패널 등 재사용 UI
│   ├── shared/         # 백엔드 연결 등 공용 연동 코드
│   ├── services/       # 상담 흐름, API payload, 위치 변환 등 화면 밖 로직
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
- `src/api_client.py`: 백엔드 `/api/chat`, `/api/chat/mock` 호출을 담당하는 클라이언트
- `src/response_renderer.py`: 백엔드 `ChatResponse` JSON을 Streamlit 컴포넌트로 렌더링
- `src/pages/first_page.py`: 기본정보 입력 후 채팅형 상담으로 넘어가는 첫 번째 페이지
- `src/pages/second_page.py`: 주요 법령을 분야별로 정리해서 보여주는 두 번째 페이지
- `src/components/`: 상담 시작 버튼, 기본정보 입력 폼, 입력정보 요약, 채팅 패널, 페이지 hero
- `src/shared/backend.py`: 백엔드 API 연결과 payload 구성
- `src/services/consultation_flow.py`: 상담 질문 제출, 모호한 질문 보정, 임시 응답 선택
- `src/services/geolocation.py`: 현재 위치를 지역 문자열로 변환하는 역지오코딩
- `src/styles/app.css`: Streamlit 전역 CSS
- `src/data/legal_data.py`: 검색 화면과 법령 정리 화면에서 사용하는 임시 법령 데이터

## 프론트 응답 JSON 스키마

프론트는 백엔드 응답을 다음과 같은 고정된 JSON 구조로 받는 것을 권장합니다.

```json
{
  "summary": "...",
  "details": ["..."],
  "laws": [{"name": "...", "article": "..."}],
  "table": {"headers": ["..."], "rows": [["...", "..."]]},
  "sources": ["..."],
  "warning": "..."
}
```

## 프론트 UI 설계 요약

- 응답 구조 고정 → Markdown 출력 대신 구조화된 JSON 기반 렌더링
- 첫 화면 기본정보 입력 → 상담 시작 후 채팅형 질문/답변으로 진행
- Streamlit 컴포넌트로 안정적으로 표시
  - `st.dataframe`, `st.expander`, `st.info`, `st.warning`, `st.chat_message`
- citation / 출처는 별도 패널로 분리
- 긴 답변은 `st.expander` 또는 `st.tabs`로 접기

## 임시 응답 기반 테스트

현재 `src/services/consultation_flow.py`가 백엔드 연결 전 상담 흐름을 확인할 수 있는 임시 응답을 제공합니다.

## 추가 문서

- `frontend_design.md`: 프론트 설계 가이드 문서
- `frontend_usecases.md`: 사용자 유스케이스와 렌더링 화면 요소 매핑 문서

## Environment

- 예시 파일: `.env.example`
- 실제 로컬 환경 파일: `.env` (커밋 금지)
- 환경 변수는 `STREAMLIT_` prefix를 사용하며 `src/settings.py`에서 pydantic-settings로 로딩합니다.
- `STREAMLIT_USE_BACKEND_API=false`: Streamlit 임시 데이터 기반 개발 모드
- `STREAMLIT_USE_BACKEND_API=true`: 백엔드 `/api/chat` 호출 모드
- `STREAMLIT_BACKEND_BASE_URL`: 백엔드 API 서버 주소

AI API key, DB URL, RAG 연결 정보는 프론트가 아니라 `backend/.env`에서 관리합니다.
