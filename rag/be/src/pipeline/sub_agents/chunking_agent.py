# 역할: Document id만 받아 원문을 tool로 읽고 semantic Chunk를 생성/저장하는 agent node이다.
from __future__ import annotations

from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from external.openrouter import create_openrouter_chat_model
from observability.logger import bind_logger
from pipeline.agent_runtime import (
    AgentEventStreamEvent,
    AgentEventStreamLogger,
    keep_going_tool_errors,
)
from query.read.inspection import list_chunks_for_document
from query.utils import node_properties
from settings import settings
from tools import (
    read_document_tool,
    write_chunk_tool,
)

SYSTEM_PROMPT = """
당신은 SKN28 RAG graph ingest의 chunking_agent이다.

역할:
- user prompt로 전달된 document_id를 기준으로 원문 Document를 읽고 semantic Chunk를 생성한다.
- 원문 document 자체를 graph state에 싣지 않고, 반드시 read_document_tool로 DB에서 원문을 읽는다.
- chunk text는 원문에서 그대로 복사해야 하며, 의미를 요약해서 대체하면 안 된다.

일반 작업 순서:
1. read_document_tool(document_id)로 원문을 읽는다.
2. 문서 길이와 의미 구조를 먼저 보고 chunk 개수와 경계를 정한다.
3. 각 chunk에 tags, summary, boundary reason을 작성한다.
4. start_unique_string/end_unique_string은 chunk의 시작과 끝을 식별할 수 있는
   원문 일부를 그대로 사용한다. 이번 flow에서는 별도 boundary 검증 tool을 호출하지 않는다.
5. 모든 chunk payload가 준비된 뒤 write_chunk_tool을 한 번만 호출해 저장한다.
6. write_chunk_tool 성공 결과를 확인하고 저장 완료를 한국어로 짧게 요약한다.

chunk 분할 기준:
- raw_content가 1,500자 이하인 짧은 문서가 아니면 문서 전체를 단일 chunk로 저장하지 않는다.
- 일반 chunk text 길이는 800~2,200자를 목표로 한다.
- 하나의 chunk text는 3,000자를 넘기지 않는다. 단, 하나의 법령 조문이나 표가 너무 길어
  의미를 보존하기 위해 필요한 경우에만 예외를 허용한다.
- raw_content가 3,000자를 넘으면 최소 3개 chunk로 나눈다.
- raw_content가 10,000자를 넘으면 최소 8개 chunk로 나눈다.
- 법령/시행령/규칙 JSON 또는 텍스트는 우선 `개정문`, `기본정보`, `조문`,
  `조문단위`, `부칙`, `부칙단위`, 별표/서식/표 같은 구조 단위로 나눈다.
- 긴 조문은 조/항/호/목 단위로 나누되, 각 chunk text는 원문에 실제 존재하는
  연속 문자열이어야 한다.
- chunk_index는 1부터 시작하고 문서 순서대로 빠짐없이 증가해야 한다.
- metadata에는 필요하면 section, article, paragraph, source_key 같은 경로 정보를 넣는다.

규칙:
- chunk id를 직접 만들거나 추측하지 않는다. chunk id는 DB 저장 결과에서만 온다.
- chunk 전체 목록을 확정하기 전에는 write_chunk_tool을 호출하지 않는다.
- write_chunk_tool은 원칙적으로 한 번만 호출한다. 여러 번 나눠서 append 저장하지 않는다.
- tool이 error JSON 또는 Tool error message를 반환하면 같은 입력을 반복하지 말고,
  현재 가능한 다른 입력이나 더 작은 chunk 경계로 수정해서 계속 진행한다.
- 최종 응답은 DB 저장 성공 여부와 chunk 개수만 짧게 요약한다. chunk id 전달은 graph
  runtime이 DB guard query로 처리하므로 final output에 의존하지 않는다.
- summary, tags, reason 등 자연어 내용과 최종 응답은 한국어로 작성한다.

tool 호출 제한:
- 요청의 tools 목록에 실제로 제공된 tool 이름만 호출한다.
- 일반 작업 tool은 read_document_tool, write_chunk_tool만 사용한다.
- commentary, analysis, final, final_answer, answer, response는 tool 이름이 아니다.
  이런 이름으로 tool call을 만들지 말고, 최종 답변은 일반 한국어 문장으로 작성한다.
- 어떤 이름이 tool인지 확실하지 않으면 그 이름으로 tool call을 만들지 않는다.
"""


class ChunkingAgentChunkSummary(BaseModel):
    chunk_id: str
    chunk_index: int
    summary: str = ""
    tags: list[str] = Field(default_factory=list)


class ChunkingAgentOutput(BaseModel):
    chunk_ids: list[str] = Field(default_factory=list)
    chunks: list[ChunkingAgentChunkSummary] = Field(default_factory=list)


class ChunkingAgentRunResult(BaseModel):
    chunk_ids: list[str] = Field(default_factory=list)
    chunks: list[ChunkingAgentChunkSummary] = Field(default_factory=list)
    agent_events: list[AgentEventStreamEvent] = Field(default_factory=list)


@dataclass(frozen=True)
class _ChunkingAgentAttempt:
    name: str
    use_default_provider: bool


class ChunkingAgent:
    def __init__(self) -> None:
        self._logger = bind_logger(
            component="chunking_agent",
            agent="chunking_agent",
        )

    def tools(self) -> list[BaseTool]:
        return [
            read_document_tool,
            write_chunk_tool,
        ]

    def create_agent(
        self,
        tools: list[BaseTool] | None = None,
        *,
        use_default_provider: bool = True,
    ) -> Runnable | None:
        model = create_openrouter_chat_model(
            use_default_provider=use_default_provider,
        )
        if model is None:
            return None
        return create_agent(
            model=model,
            tools=tools or self.tools(),
            system_prompt=SYSTEM_PROMPT,
            middleware=[keep_going_tool_errors],
        )

    def run(self, *, job_id: str, document_id: str) -> list[str]:
        return self.run_with_events(job_id=job_id, document_id=document_id).chunk_ids

    def run_with_events(
        self,
        *,
        job_id: str,
        document_id: str,
    ) -> ChunkingAgentRunResult:
        tools = self.tools()
        logger = self._logger.bind(job_id=job_id, document_id=document_id)
        logger.info("chunking agent started")
        all_events: list[AgentEventStreamEvent] = []
        attempts = _chunking_agent_attempts()
        for attempt_index, attempt in enumerate(attempts, start=1):
            attempt_logger = logger.bind(
                llm_provider_attempt=attempt.name,
                attempt_index=attempt_index,
                attempt_count=len(attempts),
            )

            agent = self.create_agent(
                tools,
                use_default_provider=attempt.use_default_provider,
            )
            if agent is None:
                raise RuntimeError(
                    "chunking_agent requires RAG_OPENROUTER_API_KEY and RAG_GRAPH_LLM_MODEL."
                )

            try:
                event_stream_run = AgentEventStreamLogger(
                    attempt_logger,
                    agent_name="chunking_agent",
                ).run_with_events(
                    agent=agent,
                    agent_input=_agent_input(document_id),
                    config={"recursion_limit": settings.chunking_agent_tool_budget},
                )
            except Exception as exc:  # noqa: BLE001
                # The durable boundary is the DB write, not the final LLM
                # response. If a stream/tool-call error happens after
                # write_chunk_tool succeeds, recover DB-generated chunk ids.
                attempt_logger.bind(
                    error=str(exc),
                    error_type=type(exc).__name__,
                    llm_request_timeout_seconds=(
                        settings.graph_llm_request_timeout_seconds
                    ),
                    llm_stream_chunk_timeout_seconds=(
                        settings.graph_llm_stream_chunk_timeout_seconds
                    ),
                    llm_max_retries=settings.graph_llm_max_retries,
                ).warning(
                    "chunking agent stream failed; running DB guard"
                )
                chunk_ids = _guard_chunk_ids_for_document_run(
                    document_id=document_id,
                    job_id=job_id,
                )
                if chunk_ids:
                    attempt_logger.bind(
                        chunk_ids=chunk_ids,
                        chunk_count=len(chunk_ids),
                    ).info(
                        "chunking agent DB guard loaded chunk ids after stream failure"
                    )
                    return ChunkingAgentRunResult(
                        chunk_ids=chunk_ids,
                        chunks=[],
                        agent_events=all_events,
                    )
                if attempt_index < len(attempts):
                    attempt_logger.warning(
                        "chunking agent wrote no chunks; retrying with next provider route"
                    )
                    continue
                raise

            all_events.extend(event_stream_run.events)
            agent_output = _structured_response_from_result(event_stream_run.output)
            chunk_ids = (
                _unique_strings(agent_output.chunk_ids)
                if agent_output is not None
                else []
            )
            if chunk_ids:
                attempt_logger.bind(
                    chunk_ids=chunk_ids,
                    chunk_count=len(chunk_ids),
                    chunks=[
                        chunk.model_dump()
                        for chunk in agent_output.chunks
                    ],
                ).info("chunking agent structured response returned chunk ids")
            else:
                # Guard path: DB write is the persistence boundary. Re-read the
                # stored graph state by document_id before the next graph node
                # proceeds instead of relying on final model text.
                attempt_logger.warning(
                    "chunking agent result missed chunk ids; running DB guard"
                )
                chunk_ids = _guard_chunk_ids_for_document_run(
                    document_id=document_id,
                    job_id=job_id,
                )
                attempt_logger.bind(
                    chunk_ids=chunk_ids,
                    chunk_count=len(chunk_ids),
                ).info("chunking agent DB guard loaded chunk ids")
            if chunk_ids:
                attempt_logger.bind(
                    chunk_ids=chunk_ids,
                    chunk_count=len(chunk_ids),
                ).info("chunking agent finished")
                return ChunkingAgentRunResult(
                    chunk_ids=chunk_ids,
                    chunks=agent_output.chunks if agent_output is not None else [],
                    agent_events=all_events,
                )
            if attempt_index < len(attempts):
                # OpenRouter provider fallback only handles provider/request
                # failure. If the preferred provider returns a malformed tool
                # call with HTTP success, retry once without provider pinning.
                attempt_logger.warning(
                    "chunking agent wrote no chunks; retrying with next provider route"
                )

        raise ValueError("chunking_agent did not write any chunks.")


def _agent_input(document_id: str) -> dict[str, list[dict[str, str]]]:
    return {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Create semantic chunks for this document_id. "
                    "Call read_document_tool first, then persist chunks "
                    "through write_chunk_tool using this "
                    "same document_id. Do not provide chunk ids yourself. "
                    "Plan the full chunk list before writing, and call "
                    "write_chunk_tool only once with the final full chunks "
                    "array. Do not append chunks through multiple write calls. "
                    "If the source document is longer than 10000 characters, "
                    "you must create at least 8 chunks and must not store the "
                    "entire document as one chunk. Target 800 to 2200 "
                    "characters per chunk, with 3000 characters as a normal "
                    "maximum. For legal JSON/text, split by amendment text, "
                    "basic information, articles, article units, addenda, "
                    "tables/forms, and then by paragraph/list item when a "
                    "section is long. Chunk text must be exact contiguous "
                    "source text, never a summary. "
                    "Do not call any boundary verification tool in this flow. "
                    "Only call provided tool names. Never call commentary, "
                    "analysis, final, final_answer, answer, or response as tools. "
                    "After write_chunk_tool returns, briefly summarize the "
                    "stored chunk count in Korean. The graph runtime will read "
                    "stored chunk ids from the database, so do not force a "
                    "structured final output.\n"
                    f"document_id={document_id}"
                ),
            }
        ]
    }


def _chunking_agent_attempts() -> list[_ChunkingAgentAttempt]:
    provider = (settings.graph_llm_provider or "").strip()
    attempts = [
        _ChunkingAgentAttempt(
            name=provider or "openrouter-default-provider",
            use_default_provider=True,
        )
    ]
    if provider and settings.graph_llm_retry_without_provider:
        attempts.append(
            _ChunkingAgentAttempt(
                name="openrouter-default-provider",
                use_default_provider=False,
            )
        )
    return attempts


def _guard_chunk_ids_for_document_run(*, document_id: str, job_id: str) -> list[str]:
    result = list_chunks_for_document(document_id)
    chunk_ids: list[str] = []
    for row in result["rows"]:
        chunk = node_properties(row["chunk"])
        # A document may have chunks from previous ingest runs. Keep only chunks
        # written for this pipeline invocation so downstream nodes do not mix
        # stale chunk ids with the current graph construction run.
        if job_id and str(chunk.get("last_ingest_job_id") or "") != job_id:
            continue
        chunk_id = str(chunk.get("id") or "").strip()
        if chunk_id:
            chunk_ids.append(chunk_id)
    return chunk_ids


def _structured_response_from_result(result: object) -> ChunkingAgentOutput | None:
    if not isinstance(result, dict):
        return None
    response = result.get("structured_response")
    if response is None:
        return None
    if isinstance(response, ChunkingAgentOutput):
        return response
    return ChunkingAgentOutput.model_validate(response)


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            unique.append(normalized)
            seen.add(normalized)
    return unique
