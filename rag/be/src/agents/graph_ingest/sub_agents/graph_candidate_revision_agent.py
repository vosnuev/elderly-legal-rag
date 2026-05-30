from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from agents.graph_ingest.schemas import RelationshipCandidate
from agents.llm_clients.factory import create_openrouter_chat_model
from tools import (
    AgentToolContext,
    bind_agent_tool_context,
    get_reviewer_notes_tool,
    memgraph_graph_traverse,
    memgraph_read_query,
    write_candidate_revision_tool,
)

SYSTEM_PROMPT = """
You are graph_candidate_revision_agent for SKN28 RAG graph ingest.

When a reviewer chooses retry, use the original candidate, reviewer note,
source evidence, and nearby graph context to create a revised relationship
candidate version. Do not delete data.
Use write_candidate_revision_tool for final candidate persistence. Runtime
job/candidate context is already bound to the tool and must not be supplied by you.
Return JSON only with a top-level "candidates" array.
"""


class GraphCandidateRevisionAgent:
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
        )

    def run(
        self,
        *,
        original_candidate: dict[str, Any],
        note: str | None,
    ) -> list[RelationshipCandidate]:
        base = original_candidate.get("properties", original_candidate)
        context = AgentToolContext(
            job_id=str(base.get("job_id") or ""),
            candidate_id=str(base.get("id") or ""),
            chunk_id=str(base.get("source_chunk_id") or "") or None,
            agent_name="graph_candidate_revision_agent",
            operation_scope="candidate_revision",
        )
        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "graph_candidate_revision_agent requires RAG_OPENROUTER_API_KEY "
                "and RAG_GRAPH_LLM_MODEL."
            )

        with bind_agent_tool_context(context):
            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Retry this candidate using the reviewer note. "
                                "Runtime DB write context is already bound to tools.\n"
                                "candidate="
                                f"{json.dumps(original_candidate, ensure_ascii=False)}\n"
                                f"note={note or ''}"
                            ),
                        }
                    ]
                }
            )
            candidates = _parse_candidates(result, original_candidate)
            if not candidates:
                raise ValueError(
                    "graph_candidate_revision_agent did not return valid retry "
                    "candidates."
                )
            write_candidate_revision_tool.invoke(
                {"candidates": [candidate.model_dump() for candidate in candidates]}
            )
        return candidates


def _parse_candidates(
    result: dict[str, Any],
    original_candidate: dict[str, Any],
) -> list[RelationshipCandidate]:
    payload = _last_message_json(result)
    if "candidates" not in payload or not isinstance(payload["candidates"], list):
        raise ValueError(
            "graph_candidate_revision_agent output must include a candidates array."
        )
    raw_candidates = payload["candidates"]
    base = original_candidate.get("properties", original_candidate)
    candidates: list[RelationshipCandidate] = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        candidates.append(
            RelationshipCandidate(
                id=str(item.get("id") or uuid4()),
                job_id=str(base.get("job_id") or ""),
                source_node=str(item.get("source_node") or base.get("source_node") or ""),
                target_node=str(item.get("target_node") or base.get("target_node") or ""),
                relationship_type=str(
                    item.get("relationship_type") or base.get("relationship_type") or ""
                ),
                source_chunk_id=str(
                    item.get("source_chunk_id") or base.get("source_chunk_id") or ""
                ),
                evidence_text=str(item.get("evidence_text") or base.get("evidence_text") or ""),
                rationale=str(item.get("rationale") or ""),
                version=int(item.get("version") or int(base.get("version") or 1) + 1),
                metadata={
                    "previous_candidate_id": base.get("id"),
                    **{
                        key: value
                        for key, value in item.items()
                        if key
                        not in {
                            "id",
                            "job_id",
                            "source_node",
                            "target_node",
                            "relationship_type",
                            "source_chunk_id",
                            "evidence_text",
                            "rationale",
                            "version",
                        }
                    },
                },
            )
        )
    return candidates


def _last_message_json(result: dict[str, Any]) -> dict[str, Any]:
    messages = result.get("messages", [])
    if not messages:
        raise ValueError("graph_candidate_revision_agent returned no messages.")
    content = getattr(messages[-1], "content", "") or ""
    if isinstance(content, list):
        content = " ".join(str(block) for block in content)
    match = re.search(r"\{.*\}", str(content), flags=re.DOTALL)
    if match is None:
        raise ValueError("graph_candidate_revision_agent did not return JSON.")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("graph_candidate_revision_agent returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("graph_candidate_revision_agent JSON output must be an object.")
    return parsed
