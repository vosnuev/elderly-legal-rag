from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from external.openrouter import create_openrouter_chat_model
from query.read.inspection import list_candidates_for_job
from query.utils import node_properties
from settings import settings
from tools import (
    MEMGRAPH_READ_TOOLS,
    get_reviewer_notes_tool,
    write_relationship_candidate_tool,
)

SYSTEM_PROMPT = """
You are graph_candidate_agent for SKN28 RAG graph ingest.

Use Memgraph tools to inspect existing schema, related entities, prior chunks,
and reviewer notes. You may use internal write tools when needed, but never
delete or destructively mutate graph data.

Generate all semantic edge candidates that are grounded in the chunk.
Do not hide candidates by ranking or filtering. Proposed semantic relationships
remain edge candidates until a reviewer approves them.
Read each chunk through Memgraph tools by chunk id before proposing candidates.
Use write_relationship_candidate_tool for final candidate persistence. Every candidate
must include left_node, right_node, relationship_type, relationship_direction,
evidence_text, and rationale. evidence_node_id is optional and should be used when a
separate Chunk, Document, or graph node grounds the candidate. The write tool generates
edge candidate ids.
Never invent edge candidate ids.
After write_relationship_candidate_tool succeeds, briefly report that candidates were
stored.
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
                                "Read and inspect this chunk id through Memgraph "
                                "tools before writing edge candidates. Use "
                                "write_relationship_candidate_tool for persistence "
                                "and use this chunk id as evidence_node_id unless "
                                "another graph node is a better evidence anchor. "
                                "Do not provide edge candidate ids yourself.\n"
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
