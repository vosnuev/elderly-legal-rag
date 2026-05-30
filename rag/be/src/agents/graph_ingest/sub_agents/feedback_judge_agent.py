from __future__ import annotations

import json
import re
from typing import Any

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from agents.graph_ingest.schemas import FeedbackJudgeResult, GraphChunk, RelationshipCandidate
from agents.llm_clients.factory import create_openrouter_chat_model
from tools import (
    AgentToolContext,
    bind_agent_tool_context,
    get_ingest_state_tool,
    memgraph_read_query,
    memgraph_schema_read,
)

SYSTEM_PROMPT = """
You are feedback_judge_agent for SKN28 RAG graph ingest.

Judge whether chunk coverage and graph relationship candidate generation are
sufficient to move to pending review. Check evidence grounding and the legal
hierarchy direction Law -> Ordinance -> EnforcementRule, including regional scope.
Return JSON only with ready_for_review, incomplete, and reason.
"""


class FeedbackJudgeAgent:
    def tools(self) -> list[BaseTool]:
        return [memgraph_schema_read, memgraph_read_query, get_ingest_state_tool]

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

    def run(
        self,
        *,
        job_id: str,
        chunks: list[GraphChunk],
        candidates: list[RelationshipCandidate],
    ) -> FeedbackJudgeResult:
        if not chunks:
            return FeedbackJudgeResult(
                ready_for_review=False,
                incomplete=True,
                reason="No chunks were produced.",
            )

        context = AgentToolContext(
            job_id=job_id,
            agent_name="feedback_judge_agent",
            operation_scope="feedback_judge",
        )
        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "feedback_judge_agent requires RAG_OPENROUTER_API_KEY and RAG_GRAPH_LLM_MODEL."
            )

        with bind_agent_tool_context(context):
            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Runtime ingest state context is already bound to "
                                "tools.\n"
                                f"chunk_count={len(chunks)}\n"
                                f"candidate_count={len(candidates)}\n"
                                "Judge whether this ingest can move to pending review."
                            ),
                        }
                    ]
                }
            )
        parsed = _last_message_json(result)
        return FeedbackJudgeResult(
            ready_for_review=bool(parsed.get("ready_for_review", True)),
            incomplete=bool(parsed.get("incomplete", False)),
            reason=str(parsed.get("reason") or ""),
        )


def _last_message_json(result: dict[str, Any]) -> dict[str, Any]:
    messages = result.get("messages", [])
    if not messages:
        raise ValueError("feedback_judge_agent returned no messages.")
    content = getattr(messages[-1], "content", "") or ""
    if isinstance(content, list):
        content = " ".join(str(block) for block in content)
    match = re.search(r"\{.*\}", str(content), flags=re.DOTALL)
    if match is None:
        raise ValueError("feedback_judge_agent did not return JSON.")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("feedback_judge_agent returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("feedback_judge_agent JSON output must be an object.")
    return parsed
