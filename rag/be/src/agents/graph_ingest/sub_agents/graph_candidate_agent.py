from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from agents.graph_ingest.schemas import GraphChunk, RelationshipCandidate
from agents.llm_clients.factory import create_openrouter_chat_model
from settings import settings
from tools import (
    AgentToolContext,
    MEMGRAPH_READ_TOOLS,
    bind_agent_tool_context,
    get_reviewer_notes_tool,
    write_relationship_candidate_tool,
)

SYSTEM_PROMPT = """
You are graph_candidate_agent for SKN28 RAG graph ingest.

Use Memgraph tools to inspect existing schema, related entities, prior chunks,
and reviewer notes. You may use internal write tools when needed, but never
delete or destructively mutate graph data.

Generate all semantic relationship candidates that are grounded in the chunk.
Do not hide candidates by ranking or filtering. Proposed semantic relationships
remain review candidates until a reviewer approves them.
Use write_relationship_candidate_tool for final candidate persistence. Runtime
job/document/chunk context is already bound to the tool and must not be supplied by you.
Return JSON only with a top-level "candidates" array.
"""


class GraphCandidateAgent:
    def tools(self) -> list[BaseTool]:
        return [
            *MEMGRAPH_READ_TOOLS,
            write_relationship_candidate_tool,
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

    def run(self, *, job_id: str, chunks: list[GraphChunk]) -> list[RelationshipCandidate]:
        candidates: list[RelationshipCandidate] = []
        for chunk in chunks:
            context = AgentToolContext(
                job_id=job_id,
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                agent_name="graph_candidate_agent",
                operation_scope="candidate_generation",
            )
            tools = self.tools()
            agent = self.create_agent(tools)
            if agent is None:
                raise RuntimeError(
                    "graph_candidate_agent requires RAG_OPENROUTER_API_KEY and "
                    "RAG_GRAPH_LLM_MODEL."
                )
            with bind_agent_tool_context(context):
                result = agent.invoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "Runtime DB write context is already bound to "
                                    "tools.\n"
                                    f"chunk_text:\n{chunk.text}"
                                ),
                            }
                        ]
                    },
                    config={"recursion_limit": settings.graph_candidate_tool_budget},
                )
                chunk_candidates = _parse_candidates(result, job_id, chunk)
                if chunk_candidates:
                    write_relationship_candidate_tool.invoke(
                        {
                            "candidates": [
                                candidate.model_dump()
                                for candidate in chunk_candidates
                            ]
                        },
                    )
            candidates.extend(chunk_candidates)
        return candidates


def _parse_candidates(
    result: dict[str, Any],
    job_id: str,
    chunk: GraphChunk,
) -> list[RelationshipCandidate]:
    payload = _last_message_json(result)
    if "candidates" not in payload or not isinstance(payload["candidates"], list):
        raise ValueError("graph_candidate_agent output must include a candidates array.")
    raw_candidates = payload["candidates"]
    candidates: list[RelationshipCandidate] = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        relationship_type = str(item.get("relationship_type") or "").strip()
        source_node = str(item.get("source_node") or item.get("source") or "").strip()
        target_node = str(item.get("target_node") or item.get("target") or "").strip()
        evidence_text = str(item.get("evidence_text") or item.get("evidence") or "").strip()
        rationale = str(item.get("rationale") or "").strip()
        if not relationship_type or not source_node or not target_node or not evidence_text:
            continue
        candidates.append(
            RelationshipCandidate(
                id=str(item.get("id") or uuid4()),
                job_id=job_id,
                source_node=source_node,
                target_node=target_node,
                relationship_type=relationship_type,
                source_chunk_id=str(item.get("source_chunk_id") or chunk.id),
                evidence_text=evidence_text,
                rationale=rationale,
                metadata={
                    key: value
                    for key, value in item.items()
                    if key
                    not in {
                        "id",
                        "source_node",
                        "source",
                        "target_node",
                        "target",
                        "relationship_type",
                        "source_chunk_id",
                        "evidence_text",
                        "evidence",
                        "rationale",
                    }
                },
            )
        )
    return candidates


def _last_message_json(result: dict[str, Any]) -> dict[str, Any]:
    messages = result.get("messages", [])
    if not messages:
        raise ValueError("graph_candidate_agent returned no messages.")
    content = getattr(messages[-1], "content", "") or ""
    if isinstance(content, list):
        content = " ".join(str(block) for block in content)
    match = re.search(r"\{.*\}", str(content), flags=re.DOTALL)
    if match is None:
        raise ValueError("graph_candidate_agent did not return JSON.")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("graph_candidate_agent returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("graph_candidate_agent JSON output must be an object.")
    return parsed
