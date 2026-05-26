from schemas.chat import(
    ChatRequest,
    ChatResponse,
    ClarificationOption,
    QuestionType,
    ResponseKind,
)

def create_clarification_response(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        kind=ResponseKind.CLARIFICATION,
        question_type=QuestionType.BROAD_OR_AMBIGUOUS,
        summary="질문 범위를 먼저 좁혀 주세요.",
        details=[
            "아래 보기 중 가장 가까운 항목을 선택해 주세요.",
            "해당하는 보기가 없으면 기타에 직접 입력해 주세요.",
        ],
        options=[
            ClarificationOption(
                id="1",
                title="복지서비스 찾기",
                description="받을 수 있는 복지 서비스와 신청 방법을 찾습니다.",
                search_focus="노인 복지서비스 지원 대상 신청 방법",
            ),
            ClarificationOption(
                
            )
        ]
    )