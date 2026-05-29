# Form Update Instructions

## 선택지 수정

`consultation_form.py`의 `SUBJECT_OPTIONS`, `GOAL_OPTIONS`, `STAGE_OPTIONS`를 수정합니다.

- 선택지는 사용자가 바로 고를 수 있는 짧은 한국어 문구로 유지합니다.
- backend DTO 필드를 늘리기 위해 선택지를 추가하지 않습니다.
- 선택지 의미는 `build_initial_context_message()`가 만드는 상담 컨텍스트 문장에 자연스럽게 들어가야 합니다.
- 선택지 목록에는 "여기에 없어요"를 유지해 사용자가 맞는 항목을 찾지 못했을 때 pass할 수 있게 합니다.
- "아직 모르겠음"처럼 사용자가 판단을 미룰 수 있는 값을 하나 유지합니다.

## 필드 추가

필드가 정말 필요한지 먼저 확인합니다.

- backend agent가 답변 품질을 높이는 데 직접 쓰는 정보인지 확인합니다.
- 단순 UI 편의값이면 `metadata`에 넣지 말고 frontend state로만 유지합니다.
- 법률/복지 판단에 필요한 정보라면 `ConsultationFormData`, `build_form_display_items()`, `_build_context_lines()`를 함께 업데이트합니다.
- 새 필드는 `README.md`의 필드 표에도 추가합니다.

## Backend 계약

Streamlit frontend는 backend `/chat` 계약을 따릅니다.

```json
{
  "session_id": "streamlit-generated-session-id",
  "message": "이번 턴의 사용자 메시지 또는 첫 턴 context + 메시지",
  "metadata": {
    "source": "streamlit",
    "turn_index": 1,
    "context_seeded": true
  }
}
```

form 데이터를 `question`, `input_mode`, `user_profile` 같은 별도 frontend DTO로 쪼개지 않습니다. backend가 agent memory를 붙이면 `session_id`를 `thread_id`로 사용하고, frontend는 전체 대화 history를 재전송하지 않습니다.

## 검증 기준

- 첫 질문에는 `[상담 입력 컨텍스트]`가 포함됩니다.
- 두 번째 질문부터는 사용자 입력만 backend로 갑니다.
- UI에는 입력된 기본정보 요약이 표시됩니다.
- mock mode와 real backend mode가 같은 response shape을 반환합니다.
