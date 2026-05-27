from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, ValidationError

from agent.openrouter_llm import get_chat_llm
from prompt import create_clarification_prompt, create_grounded_answer_prompt
from schemas.chat import(
    ChatRequest,
    ChatResponse,
    ClarificationOption,
    QuestionType,
    ResponseKind,
    SourceReference,
    LawReference,
    TableData,
    EligibilityAssessment,
    EvidenceStatus,
)

from session_store import ConversationTurn
from settings import settings
from logger import get_logger

logger = get_logger(__name__)

# LLM이 생성한 보기 3개 파싱 출력 모델
class ClarificationOptionOutput(BaseModel):
    options : list[ClarificationOption] = Field(..., min_length=3, max_length=3)

# 사용자 기본정보를 prompt에 넣을 문자열로 변환
def _profile_context(request: ChatRequest) -> str:
    profile = request.user_profile
    if profile is None:
        return "사용자 기본정보 없음"

    location = profile.location
    location_text = "위치 정보 없음"
    if location:
        parts = [location.city, location.district, location.town]
        location_text = " ".join(part for part in parts if part) or "위치 정보 없음"

    return "\n".join(
        [
            f"나이 : {profile.age if profile.age is not None else '미입력'}",
            f"거주지 : {location_text}",
            f"월소득 : {profile.monthly_income_krw if profile.monthly_income_krw is not None else '미입력'}원",
            f"가구원 수 : {profile.household_size if profile.household_size is not None else '미입력'}",
            f"소득 메모 : {profile.income_note or '없음'}",
        ]
    )


# 텍스트에 지정한 키워드 중 하나라도 들어있는지 확인
def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


# 질문 의도에 따라 RAG 검색에 보조로 붙일 사용자 정보 조건 선정
def _profile_search_terms(request: ChatRequest, primary_text: str) -> list[str]:
    profile = request.user_profile
    if profile is None:
        return []

    terms: list[str] = []
    normalized = primary_text.replace(" ", "")

    age_keywords = ("나이", "연령", "대상", "자격", "조건", "노인", "어르신", "고령", "시니어")
    income_keywords = ("소득", "중위소득", "재산", "가구", "수급", "기초연금", "지원금", "자격", "조건", "대상")
    location_keywords = (
        "지역",
        "거주",
        "동네",
        "근처",
        "주변",
        "지자체",
        "시청",
        "구청",
        "군청",
        "주민센터",
        "행정복지센터",
        "관할",
    )

    if profile.age is not None and _contains_any(normalized, age_keywords):
        terms.append(f"{profile.age}세")

    location = profile.location
    if location is not None:
        location_parts = [location.city, location.district, location.town]
        location_text = " ".join(part for part in location_parts if part)
        explicit_location = any(part and part.replace(" ", "") in normalized for part in location_parts)
        if location_text and (_contains_any(normalized, location_keywords) or explicit_location):
            terms.append(location_text)

    if _contains_any(normalized, income_keywords):
        if profile.monthly_income_krw is not None:
            terms.append(f"월소득 {profile.monthly_income_krw}원")
        if profile.household_size is not None:
            terms.append(f"{profile.household_size}인 가구")
        if profile.income_note:
            terms.append(profile.income_note)

    return terms


# backend 내부에서 쓰는 RAG 검색 문서 모델
class RetrievedDocument(BaseModel):
    content : str
    source : SourceReference
    score : float | None = Field(default=None, ge=0)


# RAG 서버의 검색 결과 item 응답 모델
class RagSearchResult(BaseModel):
    content: str
    source_title: str
    file_name: str | None = None
    file_type: str | None = None
    location: str | None = None
    url: str | None = None
    score: float | None = Field(default=None, ge=0)


# RAG 서버의 검색 응답 전체 모델
class RagSearchResponse(BaseModel):
    query: str
    results: list[RagSearchResult] = Field(default_factory=list)


# RAG 검색 호출 실패를 표현하는 예외
class RagSearchError(RuntimeError):
    pass


# 출처 표시용 긴 원문 -> 짧은 발췌문으로 축소
def _excerpt(text: str, limit: int = 500) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


# 사용자에게 보여줄 출처 라벨 문자열 생성
def _source_label(document: RetrievedDocument) -> str:
    source = document.source
    parts = [source.title]

    if source.file_name:
        parts.append(source.file_name)
    if source.section:
        parts.append(source.section)
    if document.score is not None:
        parts.append(f"score={document.score:.2f}")

    return " / ".join(parts)


# LLM 실패 시, 반환할 검색 결과 상세 문장 생성
def _documents_to_details(query: str, documents: list[RetrievedDocument]) -> list[str]:
    details = [f"검색에 사용한 질문 : {query}", "RAG 검색 결과:"]

    for index, document in enumerate(documents, start=1):
        details.append(
            "\n".join(
                [
                    f"{index}. {_source_label(document)}",
                    _excerpt(document.content),
                ]
            )
        )

    return details


# RAG 검색 서버 호출해 검색 문서를 가져옴
def _retrieve_documents(query: str) -> list[RetrievedDocument]:
    payload = {
        "query": query,
        "top_k": settings.rag_search_top_k,
    }
    request = Request(
        settings.rag_search_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    timeout = settings.rag_search_timeout_ms / 1000

    logger.info(
        "rag search request url=%s top_k=%s",
        settings.rag_search_url,
        settings.rag_search_top_k,
    )

    if settings.log_llm_context:
        logger.debug("rag search query=%s", query)

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RagSearchError(f"RAG 검색 서버가 HTTP {exc.code} 응답을 반환했습니다.") from exc
    except TimeoutError as exc:
        raise RagSearchError("RAG 검색 서버 요청 시간이 초과되었습니다.") from exc
    except URLError as exc:
        raise RagSearchError(f"RAG 검색 서버에 연결할 수 없습니다: {exc.reason}") from exc

    try:
        search_response = RagSearchResponse.model_validate_json(response_body)
    except (ValidationError, ValueError) as exc:
        raise RagSearchError("RAG 검색 서버 응답 형식이 올바르지 않습니다.") from exc

    logger.info("rag search response count=%d", len(search_response.results))

    return [
        RetrievedDocument(
            content=result.content,
            source=SourceReference(
                title=result.source_title,
                file_name=result.file_name,
                url=result.url,
                section=result.location,
                excerpt=_excerpt(result.content),
                score=result.score,
            ),
            score=result.score,
        )
        for result in search_response.results
    ]

# 원 질문 + 선택/기타 의도 = RAG 검색 쿼리 생성
def _build_rag_query(request: ChatRequest) -> str:
    primary_terms = [request.question]

    if request.selected_option is not None:
        selected = request.selected_option
        primary_terms.append(selected.search_focus or selected.title)

    if request.custom_intent:
        primary_terms.append(request.custom_intent)

    primary_text = " ".join(primary_terms)
    lines = [primary_text]

    profile_terms = _profile_search_terms(request, primary_text)
    if profile_terms:
        lines.append(" ".join(profile_terms))

    return "\n".join(lines)

# LLM 보기 생성 실패 시, 사용할 기본 보기 3개 반환
def _fallback_options() -> list[ClarificationOption]:
    return [
          ClarificationOption(
              id="1",
              title="복지서비스 찾기",
              description="받을 수 있는 복지서비스와 신청 방법을 찾습니다.",
              search_focus="노인 복지서비스 지원 대상 신청 방법",
          ),
          ClarificationOption(
              id="2",
              title="요양원/돌봄시설 찾기",
              description="요양원, 돌봄시설, 입소 조건을 찾습니다.",
              search_focus="요양원 노인요양시설 돌봄시설 입소 조건",
          ),
          ClarificationOption(
              id="3",
              title="소득 기준 혜택 찾기",
              description="소득 기준에 맞는 지원금과 혜택을 찾습니다.",
              search_focus="노인 소득 기준 복지 혜택 지원금",
          ),
      ]

# 사용자 질문에 맞는 선택 보기 3개 LLM으로 생성
def generate_clarification_options(request: ChatRequest) -> list[ClarificationOption]:
    parser = PydanticOutputParser(pydantic_object=ClarificationOptionOutput)
    prompt = create_clarification_prompt()

    try:
        chain = prompt | get_chat_llm() | parser
        result = chain.invoke(
            {
                "question" : request.question,
                "profile_context" : _profile_context(request),
                "format_instructions" : parser.get_format_instructions(),
            }
        )
        return result.options[: settings.agent_clarification_option_count]
    except Exception:
        logger.exception("clarification option generation failed")
        return _fallback_options()

# 최초 질문에 대해 보기 선택 응답 생성
def create_clarification_response(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        kind=ResponseKind.CLARIFICATION,
        question_type=QuestionType.BROAD_OR_AMBIGUOUS,
        summary="질문 범위를 먼저 좁혀 주세요.",
        details=[
            "아래 보기 중 가장 가까운 항목을 선택해 주세요.",
            "해당하는 보기가 없으면 기타에 직접 입력해 주세요.",
        ],
        options=generate_clarification_options(request),
        allow_custom_input=settings.agent_custom_input_enabled,
    )

# 사용자가 보기 1~3 중 하나를 선택 시, RAG 기반 답변 생성
def answer_with_selected_option(
    request: ChatRequest,
    history: list[ConversationTurn] | None = None,
) -> ChatResponse:
    selected = request.selected_option

    if selected is None:
        return ChatResponse(
            kind=ResponseKind.ANSWER,
            question_type=QuestionType.SEARCH,
            summary="선택한 보기가 없습니다.",
            confidence=0.0,
            evidence_status=EvidenceStatus.INSUFFICIENT,
            warning="selected_option이 없어 답변을 생성할 수 없습니다.",
        )

    query = _build_rag_query(request)
    try:
        documents = _retrieve_documents(query)
    except RagSearchError as exc:
        return ChatResponse(
            kind=ResponseKind.ANSWER,
            question_type=QuestionType.SEARCH,
            summary="RAG 검색 실패",
            details=[f"검색에 사용한 질문 : {query}"],
            sources=[],
            confidence=0.0,
            evidence_status=EvidenceStatus.RAG_ERROR,
            references=[],
            warning=str(exc),
        )

    if not documents:
        return ChatResponse(
            kind=ResponseKind.ANSWER,
            question_type=QuestionType.SEARCH,
            summary="확인 필요",
            details=[
                "RAG 서버에서 검색 결과를 찾지 못했습니다.",
                f"검색에 사용할 질문 : {query}",
            ],
            sources=[],
            confidence=0.0,
            evidence_status=EvidenceStatus.INSUFFICIENT,
            references=[],
            warning="근거 문서가 없어 정책 내용이나 자격 여부를 단정하지 않았습니다.",
        )

    return generate_grounded_answer(
        request=request,
        query=query,
        documents=documents,
        history=history,
        question_type=QuestionType.SEARCH,
    )

# 사용자가 기타 의견을 직접 입력 시, RAG 기반 답변 생성
def answer_with_custom_intent(
    request: ChatRequest,
    history: list[ConversationTurn] | None = None,
) -> ChatResponse:
    query = _build_rag_query(request)
    try:
        documents = _retrieve_documents(query)
    except RagSearchError as exc:
        return ChatResponse(
            kind=ResponseKind.ANSWER,
            question_type=QuestionType.CUSTOM_INTENT,
            summary="RAG 검색 실패",
            details=[f"검색에 사용한 질문 : {query}"],
            sources=[],
            references=[],
            confidence=0.0,
            evidence_status=EvidenceStatus.RAG_ERROR,
            warning=str(exc),
        )

    if not documents:
        return ChatResponse(
            kind=ResponseKind.ANSWER,
            question_type=QuestionType.CUSTOM_INTENT,
            summary="확인 필요",
            details=[
                "RAG 서버에서 검색 결과를 찾지 못했습니다.",
                f"검색에 사용할 질문 : {query}",
            ],
            sources=[],
            references=[],
            confidence=0.0,
            evidence_status=EvidenceStatus.INSUFFICIENT,
            warning="근거 문서가 없어 정책 내용이나 자격 여부를 단정하지 않았습니다."
        )

    return generate_grounded_answer(
        request=request,
        query=query,
        documents=documents,
        history=history,
        question_type=QuestionType.CUSTOM_INTENT,
    )

# 후속 질문 + 이전 대화 맥락 = RAG 기반 답변 생성
def answer_with_follow_up(
    request: ChatRequest,
    history: list[ConversationTurn] | None = None,
) -> ChatResponse:
    recent_context = _recent_user_context(history)
    follow_up_intent = request.custom_intent or request.question
    custom_intent = (
        f"{recent_context}\n{follow_up_intent}"
        if recent_context
        else follow_up_intent
    )

    request = request.model_copy(
        update={
            "custom_intent": custom_intent,
        }
    )
    response = answer_with_custom_intent(request, history)
    return response.model_copy(update={"question_type": QuestionType.FOLLOW_UP})

# LLM이 생성한 근거 기반 답변을 파싱하기 위한 출력 모델
class GroundedAnswerOutput(BaseModel):
    summary: str
    details: list[str] = Field(default_factory=list)
    laws: list[LawReference] = Field(default_factory=list)
    table: TableData | None = None
    eligibility: EligibilityAssessment | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_status: EvidenceStatus = EvidenceStatus.SUFFICIENT
    warning: str | None = None


# 이전 대화 기록을 prompt에 넣을 문자열로 변환
def _history_text(history: list[ConversationTurn] | None) -> str:
    if not history:
        return "이전 대화 없음"

    return "\n".join(
        f"{turn.role} : {turn.content}"
        for turn in history[-6:]
    )


# 최근 사용자 발화만 모아 후속 질문 검색 맥락으로 생성
def _recent_user_context(history: list[ConversationTurn] | None) -> str:
    if not history:
        return ""

    user_turns = [turn.content for turn in history if turn.role == "user"]
    return "\n".join(user_turns[-3:])


# 검색 문서 목록을 LLM prompt에 넣을 근거 문자열로 변환
def _documents_context(documents: list[RetrievedDocument]) -> str:
    blocks: list[str] = []

    for index, document in enumerate(documents, start=1):
        source = document.source
        blocks.append(
            "\n".join(
                [
                    f"[{index} {source.title}]",
                    f"file: {source.file_name or '-'}",
                    f"section: {source.section or '-'}",
                    f"url: {source.url or '-'}",
                    f"content: {document.content}",
                ]
            )
        )
    return "\n\n".join(blocks)

# 검색된 RAG 근거를 바탕으로 최종 상담 답변 생성
def generate_grounded_answer(
    request: ChatRequest,
    query: str,
    documents: list[RetrievedDocument],
    history: list[ConversationTurn] | None = None,
    question_type: QuestionType = QuestionType.SEARCH,
) -> ChatResponse:
    parser = PydanticOutputParser(pydantic_object=GroundedAnswerOutput)
    prompt = create_grounded_answer_prompt()

    try:
        chain = prompt | get_chat_llm() | parser
        answer = chain.invoke(
            {
                "question": request.question,
                "query": query,
                "profile_context": _profile_context(request),
                "history": _history_text(history),
                "documents_context": _documents_context(documents),
                "format_instructions": parser.get_format_instructions(),
            },
        )
    except Exception:
        logger.exception("grounded answer generation failed")
        return ChatResponse(
            kind=ResponseKind.ANSWER,
            question_type=question_type,
            summary="RAG 서버에서 관련 문서를 찾았습니다.",
            details=_documents_to_details(query, documents),
            sources=[_source_label(document) for document in documents],
            confidence=0.5,
            evidence_status=EvidenceStatus.LLM_FALLBACK,
            references=[document.source for document in documents],
            warning="LLM 답변 생성에 실패해 검색 결과를 그대로 반환했습니다.",
        )

    return ChatResponse(
        kind=ResponseKind.ANSWER,
        question_type=question_type,
        summary=answer.summary,
        details=answer.details,
        laws=answer.laws,
        table=answer.table,
        sources=[_source_label(document) for document in documents],
        references=[document.source for document in documents],
        eligibility=answer.eligibility,
        confidence=answer.confidence,
        evidence_status=answer.evidence_status,
        warning=answer.warning,
    )
