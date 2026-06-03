# 역할: review 결과와 ReviewNote를 종합해 agent Memory 문서 전체를 갱신하는 agent node이다.
from __future__ import annotations

import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from external.openrouter import create_openrouter_chat_model
from observability.logger import bind_logger
from pipeline.agent_runtime import AgentEventStreamLogger, keep_going_tool_errors
from pipeline.sub_agents.llm_settings import (
    agent_model_name,
    agent_provider,
    agent_provider_allow_fallbacks,
    agent_thinking,
)
from query.read.inspection import list_memory
from query.utils import node_properties
from settings import settings
from tools import (
    MCP_ASSIGNED_MEMGRAPH_TOOLS,
    read_chunk_context_tool,
    write_memory_document_tool,
)

SYSTEM_PROMPT = """
당신은 SKN28 RAG graph review의 memory_update_agent이다.

역할:
- reviewer가 승인/거절한 RelationshipCandidate와 ReviewNote를 보고, 다음
  graph_candidate_agent가 항상 참고할 Memory 문서를 갱신한다.
- Memory는 append log가 아니라 현재까지의 사용자 선호와 판단 기준을 정리한 단일 문서다.
- 기존 Memory의 유효한 기준은 보존하고, 새 ReviewNote에서 반복되는 선호/금지/주의 기준을
  통합해 문서 전체를 다시 작성한다.

입력:
- current_memory: 현재 Memory(scope=global)의 content/title/version/evidence 정보.
- review_context: 이번 job_id에서 저장된 ReviewNote, candidate, left/right/evidence node context.

할 수 있는 작업:
- review_context에는 이번 job_id에서 저장된 ReviewNote와 candidate endpoint/evidence context가
  이미 들어 있다. 먼저 이 입력을 기준으로 Memory를 갱신한다.
- 필요한 경우 memgraph_schema_read로 schema를 확인하고, memgraph_read_query,
  memgraph_text_index_search, memgraph_graph_traverse로 제한된 graph context를 보강 조회할 수 있다.
- memgraph_vector_search는 이미 가진 embedding vector와 준비된 vector index가 있을 때만 사용한다.
  embedding을 새로 만드는 tool이 아니므로 무리해서 호출하지 않는다.
- 현재 candidate/evidence chunk의 더 자세한 text가 필요하면 read_chunk_context_tool을 사용한다.
- 원본 Document.raw_content 전체를 읽거나 context에 싣는 작업은 피한다.
- memgraph_read_query를 사용할 때도 raw_content, embedding vector, 전체 document 확장 조회는 피한다.

Memory 작성 규칙:
- 최종 Memory는 한국어 markdown 문서로 작성한다.
- 승인된 candidate에서 배운 선호와 거절된 candidate에서 배운 금지/주의 기준을 분리해 정리한다.
- 단순 사건 로그를 길게 나열하지 말고, 다음 candidate generation에서 사용할 수 있는 판단 기준으로
  일반화한다.
- 후보별 provenance는 필요한 만큼 candidate_id, ReviewNote id를 짧게 남긴다.
- 사용자의 note가 없는 candidate는 memory 업데이트 근거로 과대해석하지 않는다.
- 기존 Memory와 충돌하는 새 기준이 있으면 새 ReviewNote 근거를 바탕으로 더 구체적인 기준을 우선한다.

저장 규칙:
- 반드시 write_memory_document_tool을 호출해 갱신된 Memory 문서 전체를 저장한다.
- write_memory_document_tool에는 content 전체, update_summary, evidence_review_note_ids,
  evidence_candidate_ids를 넣는다.
- write_memory_document_tool 외의 write tool은 제공되지 않는다.

응답 규칙:
- tool schema field 이름과 DB id는 그대로 유지한다.
- 자연어 설명과 최종 응답은 한국어로 작성한다.
- 제공된 tool 이름만 호출한다. commentary, analysis, final, final_answer, answer, response는
  tool 이름이 아니다.
"""


class MemoryUpdateAgent:
    def __init__(self) -> None:
        self._logger = bind_logger(
            component="memory_update_agent",
            agent="memory_update_agent",
        )

    def tools(self) -> list[BaseTool]:
        return [
            # Memory update agent는 필요할 때 graph context를 직접 확인할 수 있다.
            # raw Document 전체를 읽는 tool은 제공하지 않는다.
            *MCP_ASSIGNED_MEMGRAPH_TOOLS,
            read_chunk_context_tool,
            # 최종 Memory 문서 전체를 versioned update로 저장하는 유일한 write tool.
            write_memory_document_tool,
        ]

    def create_agent(self, tools: list[BaseTool] | None = None) -> Runnable | None:
        model = create_openrouter_chat_model(
            model_name=agent_model_name(
                settings,
                "memory_update_agent_llm_model",
            ),
            use_default_provider=False,
            provider=agent_provider(
                settings,
                "memory_update_agent_llm_provider",
            ),
            allow_provider_fallbacks=agent_provider_allow_fallbacks(
                settings,
                "memory_update_agent_llm_provider_allow_fallbacks",
            ),
            thinking=agent_thinking(
                settings,
                "memory_update_agent_llm_thinking",
            ),
        )
        if model is None:
            return None
        return create_agent(
            model=model,
            tools=tools or self.tools(),
            system_prompt=SYSTEM_PROMPT,
            middleware=[keep_going_tool_errors],
        )

    def run(
        self,
        *,
        job_id: str,
        current_memory: dict[str, Any],
        review_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        previous_version = int(current_memory.get("version") or 0)
        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "memory_update_agent requires RAG_OPENROUTER_API_KEY and "
                "RAG_GRAPH_LLM_MODEL."
            )

        logger = self._logger.bind(
            job_id=job_id,
            review_note_count=len(review_context),
            previous_memory_version=previous_version,
        )
        logger.info("memory update agent started")
        AgentEventStreamLogger(
            logger,
            agent_name="memory_update_agent",
            agent_context={"job_id": job_id},
        ).run(
            agent=agent,
            agent_input=_agent_input(
                job_id=job_id,
                current_memory=current_memory,
                review_context=review_context,
            ),
            config={"recursion_limit": settings.memory_update_agent_tool_budget},
        )

        memory = _latest_memory()
        version = int(memory.get("version") or 0)
        if version <= previous_version:
            raise ValueError("memory_update_agent did not update Memory document.")
        logger.bind(memory_id=memory.get("id"), version=version).info(
            "memory update agent finished"
        )
        return memory


def _agent_input(
    *,
    job_id: str,
    current_memory: dict[str, Any],
    review_context: list[dict[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    return {
        "messages": [
            {
                "role": "user",
                "content": (
                    "아래 job_id의 review note와 candidate context를 바탕으로 "
                    "Memory 문서 전체를 갱신하라. review_context에 이미 이번 review "
                    "feedback과 candidate context가 들어 있으므로 이를 우선 사용하라. "
                    "필요한 경우 read tools로 추가 graph context를 확인하되 raw "
                    "Document.raw_content 전체를 읽지 마라. "
                    "마지막에는 반드시 write_memory_document_tool을 호출해 content 전체를 "
                    "저장하라.\n"
                    f"job_id={job_id}\n"
                    "current_memory=\n"
                    f"{json.dumps(current_memory, ensure_ascii=False)}\n"
                    "review_context=\n"
                    f"{json.dumps(review_context, ensure_ascii=False)}"
                ),
            }
        ]
    }


def _latest_memory() -> dict[str, Any]:
    result = list_memory(scope="global", status="active", limit=1)
    rows = result.get("rows") or []
    if not rows:
        return {}
    return node_properties(rows[0].get("memory"))
