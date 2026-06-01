# 역할: embedded chunk와 기존 graph context를 바탕으로 relationship candidate를 생성하는 agent node이다.
from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from external.openrouter import create_openrouter_chat_model
from query.read.inspection import list_candidates_for_job
from query.utils import node_properties
from settings import settings
from tools import (
    MCP_ASSIGNED_MEMGRAPH_TOOLS,
    get_reviewer_notes_tool,
    read_chunk_tool,
    read_document_tool,
    read_memory_tool,
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
- document_id: 원본 Document node id이다.
- chunk_id: 해당 document에서 파생된 Chunk node id이며, 일반적으로 현재 candidate들의
  evidence_node_id로 사용할 수 있다.

할 수 있는 작업:
- read_memory_tool로 사용자 preference와 누적 Memory를 읽고 candidate 판단 기준에 반영한다.
- read_chunk_tool로 현재 chunk의 text, summary, tag, embedding 상태를 확인한다.
- read_document_tool로 chunk만으로 부족한 원문 document context를 보강한다.
- MCP_ASSIGNED_MEMGRAPH_TOOLS에 포함된 Memgraph read tools로 schema, 기존 node/chunk,
  text search, vector search, graph neighborhood를 탐색한다.
- get_reviewer_notes_tool로 Memory보다 더 구체적인 과거 reviewer note를 보강 검색할 수 있다.
- write_relationship_candidate_tool로 review 대상 RelationshipCandidate를 저장한다.

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
- Memory에 기록된 사용자 선호, 과거 거절/승인 기준, reviewer note와 충돌하는 후보를
  억지로 만들지 않는다.
- 후보를 ranking으로 숨기지 말고, review가 필요한 의미 있는 후보는 모두 저장한다.

응답 규칙:
- tool schema field 이름과 DB id는 그대로 유지한다.
- 자연어 설명과 최종 응답은 한국어로 작성한다.
- write_relationship_candidate_tool 성공 후에는 저장이 완료됐다는 요약을 한국어로 짧게 답한다.
"""


class GraphCandidateAgent:
    def tools(self) -> list[BaseTool]:
        return [
            # 내부 LangChain agent가 graph schema/search/traverse context를 읽는 tool bundle.
            # 외부 MCP surface는 api/mcp/server.py에서 별도 등록한다.
            *MCP_ASSIGNED_MEMGRAPH_TOOLS,
            # 현재 ingest 대상 document/chunk 원문 context를 id 기준으로 읽는 tools.
            read_document_tool,
            read_chunk_tool,
            # 사용자 feedback을 누적한 단일 Memory 문서를 읽는 tool.
            read_memory_tool,
            # 생성한 relationship candidate를 review 대기 node로 저장하는 write tool.
            write_relationship_candidate_tool,
            # 필요 시 원본 ReviewNote 검색으로 Memory보다 구체적인 feedback을 보강하는 tool.
            get_reviewer_notes_tool,
        ]

    def create_agent(
        self,
        tools: list[BaseTool] | None = None,
    ) -> Runnable | None:
        model = create_openrouter_chat_model()
        if model is None:
            return None
        return create_agent(
            model=model,
            tools=tools or self.tools(),
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, *, job_id: str, document_id: str, chunk_ids: list[str]) -> list[str]:
        previous_ids = set(_stored_candidate_ids(job_id=job_id))
        for chunk_id in chunk_ids:
            tools = self.tools()
            agent = self.create_agent(tools)
            if agent is None:
                raise RuntimeError(
                    "graph_candidate_agent requires RAG_OPENROUTER_API_KEY and "
                    "RAG_GRAPH_LLM_MODEL."
                )
            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "목표: 아래 document_id와 chunk_id를 현재 evidence "
                                "context로 삼아, review 가능한 relationship candidate를 "
                                "찾아 저장하라. 필요한 read tools를 자율적으로 사용하고, "
                                "사용자 Memory/preference를 candidate 판단에 반영하라. "
                                "candidate 저장은 write_relationship_candidate_tool을 "
                                "사용하고, edge candidate id는 직접 만들지 마라.\n"
                                f"document_id={document_id}\n"
                                f"chunk_id={chunk_id}"
                            ),
                        }
                    ]
                },
                config={"recursion_limit": settings.graph_candidate_tool_budget},
            )
            _ = result
        candidate_ids = _stored_candidate_ids(job_id=job_id)
        new_candidate_ids = [
            candidate_id
            for candidate_id in candidate_ids
            if candidate_id not in previous_ids
        ]
        return new_candidate_ids or candidate_ids


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
