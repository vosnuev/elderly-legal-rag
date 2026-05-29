# PR 요약: Streamlit 프론트 설계 및 mock UI 구현

## 변경 내용

- `streamlit/README.md`
  - Streamlit 페이지 구성과 실행 방법 정리
  - 프론트 응답 JSON 스키마 요약 추가
  - Streamlit UI/렌더링 설계 요약 추가
  - mock response 기반 테스트 페이지 및 추가 문서 안내

- `streamlit/frontend_design.md`
  - 프론트 응답 JSON 스키마 상세 정리
  - Streamlit UI/컴포넌트 설계 가이드
  - mock response 기반 프론트 구현 가이드
  - 페이지 최우선 순위 및 구현 원칙 정리

- `streamlit/frontend_usecases.md`
  - 프론트엔드 핵심 유스케이스 정리
  - 사용자 행동, 프론트엔드 책임, 렌더링 화면 요소 매핑
  - 질문 입력, 처리 상태, 답변, 근거/출처, 오류 메시지 표시 기준 정리

- `streamlit/src/views/home.py`
  - 페이지 개요 및 설계 목적 설명

- `streamlit/src/views/usecases.py`
  - 유스케이스와 화면 요소 표시 기준을 Streamlit 표로 렌더링

- `streamlit/src/views/json_schema.py`
  - 프론트 응답 계약(JSON Schema) 문서 페이지

- `streamlit/src/views/mock_ui.py`
  - mock response 기반 렌더링 테스트 페이지 구현
  - `st.dataframe`, `st.expander`, `st.info`, `st.warning` 등으로 UI 검증

- `streamlit/src/views/llm_parsing.py`
  - mock LLM 출력의 JSON, markdown 표, 리스트 파싱 테스트 페이지

- `streamlit/src/views/design_notes.py`
  - 질문 유형별 렌더링 매핑 및 citation UX 설계 노트

- `streamlit/src/app.py`
  - 사이드바 기반 페이지 네비게이션 메인으로 구성

## 목표

- 프론트는 LLM markdown 출력에 의존하지 않고 JSON 기반 응답을 안정적으로 렌더링합니다.
- 백엔드 개발 전에도 mock response로 UI 검증이 가능합니다.
- 질문 유형별 렌더링 전략과 citation UX를 미리 설계합니다.
- 사용자 유스케이스와 화면 요소를 먼저 매핑해 백엔드/RAG 연결 기준을 명확히 합니다.

## 확인 방법

```bash
cd streamlit
uv run streamlit run src/app.py
```

## 향후 연결 지점

- 백엔드 응답 스키마 확정 후 `mock_response`를 실제 API 호출로 교체
- citation 상세보기, 에러/페일백 UX 추가
- 실제 법령 문서 기반 검색 결과를 `laws`, `sources` 필드로 연결
