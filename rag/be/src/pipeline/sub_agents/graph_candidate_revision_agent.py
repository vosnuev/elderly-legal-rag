# 역할: reviewer retry 요청을 반영해 기존 relationship candidate의 수정안을 생성하는 agent node이다.
from __future__ import annotations

import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from external.openrouter import create_openrouter_chat_model
from observability.logger import bind_logger
from pipeline.agent_runtime import AgentEventStreamLogger, keep_going_tool_errors
from query.read.inspection import list_candidate_versions
from query.utils import node_properties
from settings import settings
from tools import (
    get_reviewer_notes_tool,
    memgraph_graph_traverse,
    memgraph_read_query,
    write_candidate_revision_tool,
)

SYSTEM_PROMPT = """
당신은 SKN28 RAG graph ingest의 graph_candidate_revision_agent이다.

역할:
- reviewer가 retry를 선택했을 때 기존 RelationshipCandidate를 수정한 새 candidate version을 만든다.
- original candidate, reviewer note, source evidence, 주변 graph context를 함께 고려한다.
- 기존 candidate나 graph data를 삭제하거나 파괴적으로 변경하지 않는다.

일반 작업 순서:
1. original candidate의 left_node/right_node/evidence_node_id/evidence_text/rationale을 확인한다.
2. reviewer note가 지적한 문제를 우선적으로 반영한다.
3. memgraph_read_query, memgraph_graph_traverse, get_reviewer_notes_tool로 필요한 graph context와
   과거 feedback을 보강한다.
4. 수정 candidate의 endpoint와 relationship_direction이 DB context와 reviewer note에 맞는지 확인한다.
5. write_candidate_revision_tool로 새 revision candidate를 저장한다.
6. read/search tool이 실패하면 같은 입력을 반복하지 말고 다른 read query나 주변 graph 탐색으로
   우회해서 계속 진행한다.

candidate 작성 규칙:
- previous_candidate_id에는 반드시 원본 candidate id를 전달한다.
- left_node/right_node는 proposed edge의 endpoint이고, evidence_node_id는 별도 근거 node가
  있을 때만 사용한다.
- edge_candidate id를 직접 만들거나 추측하지 않는다. id는 write tool 저장 결과에서만 온다.

응답 규칙:
- tool schema field 이름과 DB id는 그대로 유지한다.
- 자연어 설명과 최종 응답은 한국어로 작성한다.
- write_candidate_revision_tool 성공 후에는 저장이 완료됐다는 요약을 한국어로 짧게 답한다.

tool 호출 제한:
- 요청의 tools 목록에 실제로 제공된 tool 이름만 호출한다.
- commentary, analysis, final, final_answer, answer, response는 tool 이름이 아니다.
  이런 이름으로 tool call을 만들지 말고, 필요한 경우 일반 한국어 응답으로 답한다.
- 어떤 이름이 tool인지 확실하지 않으면 그 이름으로 tool call을 만들지 않는다.
"""


class GraphCandidateRevisionAgent:
    def __init__(self) -> None:
        self._logger = bind_logger(
            component="graph_candidate_revision_agent",
            agent="graph_candidate_revision_agent",
        )

    def tools(self) -> list[BaseTool]:
        return [
            memgraph_read_query,
            memgraph_graph_traverse,
            write_candidate_revision_tool,
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
            middleware=[keep_going_tool_errors],
        )

    def run(
        self,
        *,
        original_candidate: dict[str, Any],
        note: str | None,
    ) -> list[str]:
        base = original_candidate.get("properties", original_candidate)
        previous_candidate_id = str(base.get("id") or "")
        previous_revision_ids = set(
            _stored_revision_ids(previous_candidate_id=previous_candidate_id)
        )
        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "graph_candidate_revision_agent requires RAG_OPENROUTER_API_KEY "
                "and RAG_GRAPH_LLM_MODEL."
            )

        logger = self._logger.bind(previous_candidate_id=previous_candidate_id)
        logger.info("graph candidate revision agent started")
        result = AgentEventStreamLogger(
            logger,
            agent_name="graph_candidate_revision_agent",
        ).run(
            agent=agent,
            agent_input={
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Retry this candidate using the reviewer note. "
                            "Read graph context before writing revised edge "
                            "candidates. Use write_candidate_revision_tool with "
                            "previous_candidate_id and do not provide candidate ids "
                            "yourself. Only call provided tool names. Never call "
                            "commentary, analysis, final, final_answer, answer, "
                            "or response as tools.\n"
                            "candidate="
                            f"{json.dumps(original_candidate, ensure_ascii=False)}\n"
                            f"previous_candidate_id={previous_candidate_id}\n"
                            f"note={note or ''}"
                        ),
                    }
                ]
            },
            config={"recursion_limit": settings.graph_candidate_tool_budget},
        )
        _ = result
        logger.info("graph candidate revision agent finished")
        edge_candidate_ids = [
            candidate_id
            for candidate_id in _stored_revision_ids(
                previous_candidate_id=previous_candidate_id
            )
            if candidate_id not in previous_revision_ids
        ]
        if not edge_candidate_ids:
            raise ValueError("graph_candidate_revision_agent did not write revisions.")
        return edge_candidate_ids


def _stored_revision_ids(*, previous_candidate_id: str) -> list[str]:
    if not previous_candidate_id:
        return []
    result = list_candidate_versions(previous_candidate_id)
    revision_ids: list[str] = []
    for row in result["rows"]:
        for revision in row.get("revisions") or []:
            props = node_properties(revision)
            revision_id = str(props.get("id") or "").strip()
            if revision_id:
                revision_ids.append(revision_id)
    return revision_ids
