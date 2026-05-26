from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class InputMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class QuestionType(StrEnum):
    SEARCH = "search"
    GENERAL = "general"
    BROAD_OR_AMBIGUOUS = "broad_or_ambiguous"
    CUSTOM_INTENT = "custom_intent"
    FOLLOW_UP = "follow_up"


class ResponseKind(StrEnum):
    CLARIFICATION = "clarification"
    ANSWER = "answer"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    POSSIBLY_ELIGIBLE = "possibly_eligible"
    CONFIRMATION_REQUIRED = "confirmation_required"
    UNKNOWN = "unknown"


class UserLocation(BaseModel):
    city: str | None = Field(default=None, description="시/도 또는 광역 지자체")
    district: str | None = Field(default=None, description="구/군/시")
    town: str | None = Field(default=None, description="읍/면/동")
    latitude: float | None = None
    longitude: float | None = None
    detected: bool = Field(default=False, description="기기 위치 기반 자동 감지 여부")


class UserProfile(BaseModel):
    age: int | None = Field(default=None, ge=0, le=130)
    location: UserLocation | None = None
    monthly_income_krw: int | None = Field(default=None, ge=0)
    household_size: int | None = Field(default=None, ge=1)
    income_note: str | None = Field(
        default=None,
        description="소득 산정 방식이 불명확할 때 사용자가 남긴 추가 설명",
    )


class SelectedOption(BaseModel):
    id: Literal["1", "2", "3"]
    title: str
    search_focus: str | None = Field(
        default=None,
        description="RAG 검색에 결합할 의도/범위 설명",
    )


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None
    user_profile: UserProfile | None = None
    input_mode: InputMode = InputMode.TEXT
    asr_text: str | None = Field(
        default=None,
        description="음성 입력 중간/최종 인식 텍스트",
    )
    asr_final: bool = Field(default=True, description="ASR 결과가 최종 문장인지 여부")
    selected_option: SelectedOption | None = Field(
        default=None,
        description="사용자가 보기 1~3 중 선택한 항목",
    )
    custom_intent: str | None = Field(
        default=None,
        description="사용자가 기타를 선택하고 직접 입력한 추가 의도",
    )
    is_follow_up: bool = False


class LawReference(BaseModel):
    name: str
    article: str
    url: str | None = None


class TableData(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class ClarificationOption(BaseModel):
    id: Literal["1", "2", "3"]
    title: str
    description: str
    search_focus: str = Field(
        ...,
        description="선택 시 원 질문과 결합해 RAG 검색에 사용할 문장",
    )


class SourceReference(BaseModel):
    title: str = Field(..., description="문서명 또는 출처명")
    file_name: str | None = None
    url: str | None = None
    page: int | None = Field(default=None, ge=1)
    article: str | None = None
    section: str | None = None
    excerpt: str | None = Field(default=None, description="답변 근거가 된 짧은 원문")


class EligibilityAssessment(BaseModel):
    status: EligibilityStatus
    reason: str
    required_info: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    kind: ResponseKind = ResponseKind.ANSWER
    question_type: QuestionType | None = None
    summary: str = ""
    details: list[str] = Field(default_factory=list)
    laws: list[LawReference] = Field(default_factory=list)
    table: TableData | None = None
    sources: list[str] = Field(
        default_factory=list,
        description="프론트 표시용 출처 문자열 목록",
    )
    references: list[SourceReference] = Field(
        default_factory=list,
        description="RAG 검증용 상세 출처 목록",
    )
    eligibility: EligibilityAssessment | None = None
    options: list[ClarificationOption] = Field(
        default_factory=list,
        description="질문이 넓거나 모호할 때 제공하는 보기 3개",
    )
    allow_custom_input: bool = Field(
        default=False,
        description="기타 직접 입력을 허용할지 여부",
    )
    warning: str | None = None
