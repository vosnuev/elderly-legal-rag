from __future__ import annotations

import json
import re
from typing import Any

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from pipeline.schemas import FeedbackJudgeResult
from external.openrouter import create_openrouter_chat_model
from tools import (
    memgraph_graph_traverse,
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
        return [memgraph_schema_read, memgraph_read_query, memgraph_graph_traverse]

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
        document_id: str,
        chunk_ids: list[str],
        edge_candidate_ids: list[str],
    ) -> FeedbackJudgeResult:
        if not chunk_ids:
            return FeedbackJudgeResult(
                ready_for_review=False,
                incomplete=True,
                reason="No chunk ids were produced.",
            )

        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "feedback_judge_agent requires RAG_OPENROUTER_API_KEY and RAG_GRAPH_LLM_MODEL."
            )

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Use Memgraph read tools if needed.\n"
                            f"job_id={job_id}\n"
                            f"document_id={document_id}\n"
                            f"chunk_ids={chunk_ids}\n"
                            f"edge_candidate_ids={edge_candidate_ids}\n"
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
