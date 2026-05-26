from fastapi import APIRouter

from schemas.chat import (
    ChatRequest,
    ChatResponse,
    ClarificationOption,
    EligibilityAssessment,
    LawReference,
    QuestionType,
    ResponseKind,
    SourceReference,
    TableData,
    UserLocation,
    UserProfile,
)
from settings import settings
from agent.graph import(
    create_clarificaion_response,
    answer_with_selected_option,
    answer_with_custom_intent,
)

router = APIRouter(prefix="/api", tags=["chat"])


def _location_label(profile: UserProfile | None) -> str:
    location = profile.location if profile else None
    if not location:
        return "거주 지역"

    parts = [location.city, location.district, location.town]
    return " ".join(part for part in parts if part) or "거주 지역"


def _build_clarification_options(request: ChatRequest) -> list[ClarificationOption]:
    location = _location_label(request.user_profile)
    options = [
        ClarificationOption(
            id="1",
            title=f"{location} 노인 복지서비스",
            description="현재 지역에서 받을 수 있는 복지서비스와 신청 방법을 찾습니다.",
            search_focus=f"{location} 노인 복지서비스 지원 대상 신청 방법",
        ),
        ClarificationOption(
            id="2",
            title=f"{location} 요양원/돌봄시설",
            description="요양원, 노인요양시설, 돌봄시설 위치와 이용 조건을 찾습니다.",
            search_focus=f"{location} 요양원 노인요양시설 돌봄시설 입소 조건",
        ),
        ClarificationOption(
            id="3",
            title="소득 기준으로 받을 수 있는 혜택",
            description="나이, 지역, 소득 정보를 기준으로 받을 가능성이 있는 지원을 찾습니다.",
            search_focus=f"{location} 노인 소득 기준 복지 혜택 지원금",
        ),
    ]
    return options[: settings.agent_clarification_option_count]


@router.post("/chat", response_model=ChatResponse)
def create_chat_response(request: ChatRequest) -> ChatResponse:
    if request.selected_option or request.custom_intent:
        focus = request.custom_intent
        question_type = QuestionType.CUSTOM_INTENT
        if request.selected_option:
            focus = request.selected_option.search_focus or request.selected_option.title
            question_type = QuestionType.SEARCH

        return ChatResponse(
            kind=ResponseKind.ANSWER,
            question_type=question_type,
            summary="RAG 연결 전 데모 응답입니다.",
            details=[
                f"최초 질문: {request.question}",
                f"검색 방향: {focus}",
                "실제 구현에서는 이 두 정보를 합쳐 문서 검색을 수행하고, 근거가 있는 내용만 답변합니다.",
            ],
            sources=[],
            references=[],
            allow_custom_input=False,
            warning=(
                "아직 RAG 검색기가 연결되지 않아 실제 정책 판단이나 자격 판정은 하지 않았습니다."
                if settings.agent_demo_mode
                else None
            ),
        )

    return ChatResponse(
        kind=ResponseKind.CLARIFICATION,
        question_type=QuestionType.BROAD_OR_AMBIGUOUS,
        summary="질문 범위를 먼저 좁혀 주세요.",
        details=[
            "아래 보기 중 가장 가까운 항목을 선택하면 그 방향으로 근거 문서를 검색합니다.",
            "해당하는 보기가 없으면 기타에 직접 입력하면 됩니다.",
        ],
        options=_build_clarification_options(request),
        allow_custom_input=settings.agent_custom_input_enabled,
    )

@router.post("./chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if request.custom_intent:
        return answer_with_custom_intent(request)
    
    if request.selected_option:
        return answer_with_selected_option(request)
    
    return create_clarification_response(request)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ClarificationOption",
    "EligibilityAssessment",
    "LawReference",
    "router",
    "SourceReference",
    "TableData",
    "UserLocation",
    "UserProfile",
]
