from __future__ import annotations

import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from external.openrouter import create_openrouter_chat_model
from query.read.inspection import list_candidate_versions
from query.utils import node_properties
from tools import (
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
Use write_candidate_revision_tool for final candidate persistence. Pass the original
candidate id as previous_candidate_id. The write tool generates edge candidate ids.
Never invent edge candidate ids.
Use left_node/right_node for the two proposed endpoints, and evidence_node_id for
an optional separate node that grounds the revised candidate.
After write_candidate_revision_tool succeeds, briefly report that candidates were stored.
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

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Retry this candidate using the reviewer note. "
                            "Read graph context before writing revised edge "
                            "candidates. Use write_candidate_revision_tool with "
                            "previous_candidate_id and do not provide candidate ids "
                            "yourself.\n"
                            "candidate="
                            f"{json.dumps(original_candidate, ensure_ascii=False)}\n"
                            f"previous_candidate_id={previous_candidate_id}\n"
                            f"note={note or ''}"
                        ),
                    }
                ]
            }
        )
        _ = result
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
