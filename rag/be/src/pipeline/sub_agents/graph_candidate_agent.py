# 역할: embedded chunk와 기존 graph context를 바탕으로 relationship candidate를 생성하는 agent node이다.
from __future__ import annotations

import json
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor, as_completed

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
from query.read.inspection import list_candidates_for_job
from query.read.inspection import list_memory
from query.utils import node_properties
from settings import settings
from tools import (
    MCP_ASSIGNED_MEMGRAPH_TOOLS,
    read_chunk_context_tool,
    web_search_firecrawl_tool,
    write_relationship_candidate_tool,
)

SYSTEM_PROMPT = """
당신은 SKN28 RAG graph ingest의 graph_candidate_agent이다.

목표:
- user prompt로 전달되는 original document_id와 그 document에서 파생된 chunk_id를
  현재 evidence context로 삼는다.
- 주어진 read tools를 사용해 chunk끼리의 관계, chunk와 기존 graph node의 관계,
  또는 기존 graph node 사이의 관계 중 현재 chunk가 근거로 뒷받침할 수 있는 관계를 찾는다.
- 찾은 관계가 reviewer 승인 후 실제 edge로 materialize될 수 있도록 RelationshipCandidate로 저장한다.
- 후보는 확정 edge가 아니라 review 대기 artifact이다.

제공되는 context:
- document_id: 원본 Document node id이다. provenance 확인용이며, 원문 raw_content를
  읽기 위한 입력으로 사용하지 않는다.
- chunk_id: 해당 document에서 파생된 Chunk node id이며, 일반적으로 현재 candidate들의
  evidence_node_id로 사용할 수 있다.
- Agent Memory Context: runtime이 매 chunk 실행마다 직접 주입하는 장기 사용자 선호/판단
  기준이다. Memory는 tool 호출 결과가 아니며, 별도 tool을 호출하지 않아도 항상 반영해야 한다.

사용 가능한 tool과 역할:
- read_chunk_context_tool: 현재 chunk_id의 text, chunk_name, chunk_description, summary,
  tags 같은 candidate 판단용 context를 읽는다. raw embedding vector는 반환하지 않는다.
- memgraph_schema_read: 현재 DB label, relationship type, index, query 제한을 확인한다.
- memgraph_read_query: 필요한 기존 DB node/edge를 제한된 read-only Cypher로 조회한다.
  raw_content, embedding vector, 전체 Document 확장 조회는 금지한다.
- memgraph_text_index_search: 준비된 Memgraph text index에서 keyword 기반 anchor를 찾는다.
  index가 없거나 결과가 비면 실패/빈 결과가 나올 수 있다.
- memgraph_vector_search: 이미 가진 embedding vector와 준비된 vector index가 있을 때만 쓴다.
  embedding을 새로 생성하는 tool이 아니므로 무리해서 호출하지 않는다.
- memgraph_graph_traverse: 확인한 node id 주변의 제한된 graph neighborhood만 탐색한다.
  document_id에서 전체 문서를 펼치는 용도로 쓰지 않는다.
- web_search_firecrawl_tool: 내부 DB graph만으로 관계 판단 배경이 부족할 때 공개 웹 검색어를
  직접 작성해 링크/요약을 얻는다. 검색 결과는 보조 정보이며 DB node id 생성 근거가 아니다.
- write_relationship_candidate_tool: review 대상 RelationshipCandidate를 저장하는 유일한
  write tool이다.

tool 실패 처리:
- read/search tool은 DB index 미준비, 빈 결과, query 제약, timeout으로 실패할 수 있다.
- tool error를 받으면 같은 입력을 반복하지 말고 더 단순한 query나 다른 read 경로로 우회한다.
- Firecrawl은 API key, quota, timeout, 빈 검색 결과로 success=false를 반환할 수 있다.
  success=false이면 해당 검색 결과는 사용하지 않는다.

candidate 작성 규칙:
- 모든 candidate는 left_node, right_node, relationship_type, relationship_direction,
  evidence_text, rationale을 포함해야 한다.
- evidence_node_id는 관계를 뒷받침하는 Chunk/Document/graph node가 별도로 있을 때 사용한다.
  일반적으로 현재 chunk_id를 evidence_node_id로 사용한다.
- endpoint로 사용할 left_node/right_node는 DB에 실제 존재하는 node id여야 한다.
- edge_candidate id를 직접 만들거나 추측하지 않는다. id는 write tool 저장 결과에서만 온다.
- evidence_text는 현재 chunk 또는 확인한 source context에 실제로 근거가 있어야 한다.
- user prompt에 들어온 id 문자열만 보고 candidate를 만들지 않는다. candidate 저장 전에는
  반드시 read tool을 사용해 현재 chunk와 필요한 graph context를 확인한다.
- 원본 Document.raw_content 전체를 읽거나 graph_traverse/read_query 결과로 LLM context에
  싣지 않는다. 현재 근거 text는 read_chunk_context_tool이 반환한 chunk text를 사용한다.
- memgraph_graph_traverse를 사용할 때는 document_id를 시작점으로 전체 Document를 펼치지 않는다.
- Agent Memory Context에 기록된 사용자 선호, 과거 거절/승인 기준, 주의 기준과 충돌하는
  후보를 억지로 만들지 않는다.
- 외부 웹 검색은 관계 판단을 보강하기 위한 추가 정보 획득 수단이다. 검색 결과만으로
  left_node/right_node를 새로 만들지 않는다. 후보 endpoint는 Memgraph read tool 또는
  read_chunk_context_tool로 확인한 기존 DB node id여야 한다.
- 후보를 ranking으로 숨기지 말고, review가 필요한 의미 있는 후보는 모두 저장한다.

응답 규칙:
- tool schema field 이름과 DB id는 그대로 유지한다.
- 자연어 설명과 최종 응답은 한국어로 작성한다.
- write_relationship_candidate_tool 성공 후에는 저장이 완료됐다는 요약을 한국어로 짧게 답한다.

tool 호출 제한:
- 요청의 tools 목록에 실제로 제공된 tool 이름만 호출한다.
- 사용할 수 있는 read tool 이름은 memgraph_read_query, memgraph_schema_read,
  memgraph_text_index_search, memgraph_vector_search, memgraph_graph_traverse,
  read_chunk_context_tool, web_search_firecrawl_tool이다.
- 사용할 수 있는 write tool 이름은 write_relationship_candidate_tool이다.
- memgraph_query, memgraph_write_query, read_document_tool은 제공되지 않는다.
- commentary, analysis, final, final_answer, answer, response는 tool 이름이 아니다.
  이런 이름으로 tool call을 만들지 말고, 필요한 경우 일반 한국어 응답으로 답한다.
- 어떤 이름이 tool인지 확실하지 않으면 그 이름으로 tool call을 만들지 않는다.
"""


class GraphCandidateAgent:
    def __init__(self) -> None:
        self._logger = bind_logger(
            component="graph_candidate_agent",
            agent="graph_candidate_agent",
        )

    def tools(self) -> list[BaseTool]:
        return [
            # 내부 LangChain agent가 graph schema/search/traverse context를 읽는 tool bundle.
            # 외부 MCP surface는 api/mcp/server.py에서 별도 등록한다.
            *MCP_ASSIGNED_MEMGRAPH_TOOLS,
            # 현재 candidate의 evidence chunk만 읽는다. 원본 Document raw_content는
            # candidate 단계 LLM context에 싣지 않는다.
            read_chunk_context_tool,
            # DB 내부 context만으로 관계 판단 근거가 부족할 때 외부 공개 웹 evidence를
            # 보강 조회한다. 검색 결과는 DB node id 생성 근거가 아니라 보조 출처이다.
            web_search_firecrawl_tool,
            # 생성한 relationship candidate를 review 대기 node로 저장하는 write tool.
            write_relationship_candidate_tool,
        ]

    def create_agent(
        self,
        tools: list[BaseTool] | None = None,
    ) -> Runnable | None:
        model = create_openrouter_chat_model(
            model_name=agent_model_name(
                settings,
                "graph_candidate_agent_llm_model",
            ),
            use_default_provider=False,
            provider=agent_provider(
                settings,
                "graph_candidate_agent_llm_provider",
            ),
            allow_provider_fallbacks=agent_provider_allow_fallbacks(
                settings,
                "graph_candidate_agent_llm_provider_allow_fallbacks",
            ),
            thinking=agent_thinking(
                settings,
                "graph_candidate_agent_llm_thinking",
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

    def run(self, *, job_id: str, document_id: str, chunk_ids: list[str]) -> list[str]:
        previous_ids = set(_stored_candidate_ids(job_id=job_id))
        worker_count = _candidate_worker_count(len(chunk_ids))
        memory_context = _memory_context()
        self._logger.bind(
            job_id=job_id,
            document_id=document_id,
            chunk_count=len(chunk_ids),
            worker_count=worker_count,
        ).info("graph candidate agent dispatch started")

        errors: list[Exception] = []
        if worker_count == 1:
            for chunk_id in chunk_ids:
                try:
                    self._run_for_chunk(
                        job_id=job_id,
                        document_id=document_id,
                        chunk_id=chunk_id,
                        memory_context=memory_context,
                    )
                except Exception as exc:  # noqa: BLE001
                    self._logger.bind(
                        job_id=job_id,
                        document_id=document_id,
                        chunk_id=chunk_id,
                    ).exception("graph candidate agent chunk failed")
                    errors.append(exc)
        else:
            errors = self._run_chunks_concurrently(
                job_id=job_id,
                document_id=document_id,
                chunk_ids=chunk_ids,
                worker_count=worker_count,
                memory_context=memory_context,
            )

        candidate_ids = _stored_candidate_ids(job_id=job_id)
        new_candidate_ids = [
            candidate_id
            for candidate_id in candidate_ids
            if candidate_id not in previous_ids
        ]
        result_candidate_ids = new_candidate_ids or candidate_ids
        if errors:
            self._logger.bind(
                job_id=job_id,
                document_id=document_id,
                error_count=len(errors),
                candidate_count=len(result_candidate_ids),
                first_error=str(errors[0]),
            ).warning("graph candidate agent completed with chunk-level errors")
            # Candidate generation is chunk-level best effort. A provider/tool
            # validation failure for one chunk should not discard candidates
            # already written by other chunks. If no candidate survived, surface
            # the first error so the build can fail loudly.
            if not result_candidate_ids:
                raise errors[0]
        return result_candidate_ids

    def _run_chunks_concurrently(
        self,
        *,
        job_id: str,
        document_id: str,
        chunk_ids: list[str],
        worker_count: int,
        memory_context: dict[str, object],
    ) -> list[Exception]:
        # 각 chunk agent run은 외부 LLM/tool I/O가 대부분이므로 chunk 단위로 병렬화한다.
        errors: list[Exception] = []
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="graph-candidate",
        ) as executor:
            futures = {
                executor.submit(
                    copy_context().run,
                    self._run_for_chunk,
                    job_id=job_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    memory_context=memory_context,
                ): chunk_id
                for chunk_id in chunk_ids
            }
            for future in as_completed(futures):
                chunk_id = futures[future]
                logger = self._logger.bind(
                    job_id=job_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                )
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("graph candidate agent chunk failed")
                    errors.append(exc)
                else:
                    logger.info("graph candidate agent chunk completed")
        return errors

    def _run_for_chunk(
        self,
        *,
        job_id: str,
        document_id: str,
        chunk_id: str,
        memory_context: dict[str, object],
    ) -> None:
        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "graph_candidate_agent requires RAG_OPENROUTER_API_KEY and "
                "RAG_GRAPH_LLM_MODEL."
            )
        logger = self._logger.bind(
            job_id=job_id,
            document_id=document_id,
            chunk_id=chunk_id,
        )
        logger.info("graph candidate agent started")
        result = AgentEventStreamLogger(
            logger,
            agent_name="graph_candidate_agent",
            agent_context={
                "job_id": job_id,
                "document_id": document_id,
                "chunk_id": chunk_id,
            },
        ).run(
            agent=agent,
            agent_input={
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "목표: 아래 document_id와 chunk_id를 현재 evidence "
                            "context로 삼아, review 가능한 relationship candidate를 "
                            "찾아 저장하라. 필요한 read tools를 자율적으로 사용하고, "
                            "아래 Agent Memory Context를 반드시 candidate 판단에 반영하라. "
                            "Memory는 이미 runtime이 주입한 장기 기준이므로 별도 tool로 "
                            "다시 조회하려고 하지 마라. "
                            "chunk 조회는 read_chunk_context_tool을 사용하고 raw "
                            "embedding vector를 읽지 마라. "
                            "원본 Document.raw_content는 읽지 말고, document_id를 "
                            "memgraph_graph_traverse 시작점으로 사용하지 마라. "
                            "DB 내부 context가 부족하면 web_search_firecrawl_tool에 "
                            "한국어 검색어를 직접 작성해 공개 웹 배경 정보를 보강할 수 있다. "
                            "candidate 저장은 write_relationship_candidate_tool을 "
                            "사용하고, edge candidate id는 직접 만들지 마라. "
                            "제공된 tool 이름만 호출하고 commentary, analysis, "
                            "final, final_answer, answer, response를 tool로 "
                            "호출하지 마라.\n"
                            f"document_id={document_id}\n"
                            f"chunk_id={chunk_id}\n"
                            "Agent Memory Context:\n"
                            f"{json.dumps(memory_context, ensure_ascii=False)}"
                        ),
                    }
                ]
            },
            config={"recursion_limit": settings.graph_candidate_tool_budget},
        )
        _ = result
        logger.info("graph candidate agent finished")


def _stored_candidate_ids(*, job_id: str) -> list[str]:
    if not job_id:
        return []
    result = list_candidates_for_job(job_id)
    candidate_ids: list[str] = []
    for row in result["rows"]:
        candidate = node_properties(row["candidate"])
        candidate_id = str(candidate.get("id") or "").strip()
        if candidate_id:
            candidate_ids.append(candidate_id)
    return candidate_ids


def _memory_context() -> dict[str, object]:
    result = list_memory(scope="global", status="active", limit=1)
    rows = result.get("rows") or []
    if not rows:
        return {
            "scope": "global",
            "version": 0,
            "content": "",
            "note": "No Memory has been written yet.",
        }
    memory = node_properties(rows[0]["memory"])
    return {
        "scope": memory.get("scope", "global"),
        "title": memory.get("title", ""),
        "version": memory.get("version", 0),
        "content": memory.get("content", ""),
        "evidence_review_note_ids": memory.get("evidence_review_note_ids", []),
        "evidence_candidate_ids": memory.get(
            "evidence_relationship_candidate_ids",
            [],
        ),
    }


def _candidate_worker_count(chunk_count: int) -> int:
    if chunk_count <= 0:
        return 1
    return min(settings.graph_candidate_worker_count, chunk_count)
