# Streamlit Consultation Forms

이 디렉토리는 Streamlit 상담 진입 form과 form 입력값을 backend agent가 이해할 수 있는 상담 컨텍스트로 바꾸는 규칙을 관리합니다.

## 역할

- `consultation_form.py`: 상담 기본정보 입력 UI, 선택지 목록, session state 저장, 첫 턴 prompt context 생성
- `FLOW.md`: form 입력부터 backend chat 요청까지의 흐름
- `FORM_INSTRUCTIONS.md`: form 필드나 선택지를 수정할 때 지켜야 하는 기준

## v1 원칙

- frontend는 backend agent 내부 대화 history를 다시 만들지 않습니다.
- frontend는 `session_id`와 이번 턴의 사용자 입력을 보냅니다.
- form 입력값은 첫 backend 요청에 상담 컨텍스트로 seed합니다.
- 이후 turn은 같은 `session_id`를 유지하고 사용자 입력만 보냅니다.
- LangChain/LangGraph memory 연결은 backend에서 `session_id -> thread_id`로 처리합니다.

## 현재 form 필드

| 필드 | 목적 |
| --- | --- |
| 태어난 연도 | 나이 기반 정책/법률 조건을 상담 context에 포함 |
| 사는 지역 | 지역별 기관, 절차, 지원 정보 확인 |
| 누가 겪는 일인가요? | 본인/가족/근로자/사업주 등 상담 대상 구분 |
| 필요한 정보 | 지원 신청, 법령 확인, 불이익 대응 등 사용자의 목적 |
| 진행 단계 | 알아보는 중, 신청 전, 거절됨, 분쟁 발생 등 상황 단계 |
| 기타 정보 | 쉼표로 구분하는 자유 조건 |

지역은 직접 입력하거나 `내 위치 사용하기` 버튼으로 채울 수 있습니다. 상담 대상, 필요한 정보, 진행 단계에는 사용자가 맞는 항목을 찾지 못했을 때 고를 수 있도록 `여기에 없어요` 선택지를 유지합니다.

## 관련 파일

- `streamlit/src/chat_backend_client.py`: backend `/chat` 또는 mock stream client
- `streamlit/src/services/chat_flow.py`: 사용자의 turn을 backend 요청으로 넘기는 orchestration
- `streamlit/src/pages/consulting_page.py`: 상담 화면
