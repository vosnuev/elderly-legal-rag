from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from agents.graph_ingest.schemas import GraphChunk, RegisteredDocument
from agents.llm_clients.factory import create_openrouter_chat_model
from tools import (
    AgentToolContext,
    bind_agent_tool_context,
    count_occurrences_tool,
    write_chunk_tool,
)

SYSTEM_PROMPT = """
You are chunking_agent for SKN28 RAG graph ingest.

Create semantic chunks from the original document without paraphrasing source text.
Each chunk must be copied from the original document, not summarized as replacement text.
For each chunk, assign tags, a short summary, and the reason for the boundary.
Use count_occurrences_tool repeatedly to make start_unique_string and end_unique_string
that each occur exactly once in the original document.
Use write_chunk_tool for final chunk persistence. Runtime job/document context is
already bound to the tool and must not be supplied by you.
Return JSON only with a top-level "chunks" array.
"""


class ChunkingAgent:
    def tools(self) -> list[BaseTool]:
        return [count_occurrences_tool, write_chunk_tool]

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

    def run(self, *, job_id: str, document: RegisteredDocument) -> list[GraphChunk]:
        context = AgentToolContext(
            job_id=job_id,
            document_id=document.id,
            agent_name="chunking_agent",
            operation_scope="chunking",
        )
        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "chunking_agent requires RAG_OPENROUTER_API_KEY and RAG_GRAPH_LLM_MODEL."
            )

        with bind_agent_tool_context(context, raw_content=document.raw_content):
            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Create semantic chunks for this document. "
                                "Runtime DB write context is already bound to tools.\n\n"
                                f"{document.raw_content}"
                            ),
                        }
                    ]
                }
            )
            chunks = _parse_chunks(result, document)
            if not chunks:
                raise ValueError("chunking_agent did not return valid chunks.")
            write_chunk_tool.invoke({"chunks": [chunk.model_dump() for chunk in chunks]})
        return chunks


def _parse_chunks(result: dict[str, Any], document: RegisteredDocument) -> list[GraphChunk]:
    payload = _last_message_json(result)
    if "chunks" not in payload or not isinstance(payload["chunks"], list):
        raise ValueError("chunking_agent output must include a chunks array.")
    raw_chunks = payload["chunks"]
    chunks: list[GraphChunk] = []
    for index, item in enumerate(raw_chunks, start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("chunk_text") or "").strip()
        if not text or text not in document.raw_content:
            continue
        start_unique_string = str(item.get("start_unique_string") or "").strip()
        end_unique_string = str(item.get("end_unique_string") or "").strip()
        if (
            not start_unique_string
            or not end_unique_string
            or document.raw_content.count(start_unique_string) != 1
            or document.raw_content.count(end_unique_string) != 1
        ):
            continue
        start_char = document.raw_content.find(text)
        chunks.append(
            GraphChunk(
                id=str(item.get("id") or uuid4()),
                document_id=document.id,
                chunk_index=int(item.get("chunk_index") or index),
                text=text,
                tags=[str(tag) for tag in item.get("tags", []) if tag],
                summary=str(item.get("summary") or ""),
                reason=str(item.get("reason") or item.get("boundary_rationale") or ""),
                start_unique_string=start_unique_string,
                end_unique_string=end_unique_string,
                start_char=start_char,
                end_char=start_char + len(text),
            )
        )
    return chunks


def _last_message_json(result: dict[str, Any]) -> dict[str, Any]:
    messages = result.get("messages", [])
    if not messages:
        raise ValueError("chunking_agent returned no messages.")
    content = getattr(messages[-1], "content", "") or ""
    if isinstance(content, list):
        content = " ".join(str(block) for block in content)
    match = re.search(r"\{.*\}", str(content), flags=re.DOTALL)
    if match is None:
        raise ValueError("chunking_agent did not return JSON.")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("chunking_agent returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("chunking_agent JSON output must be an object.")
    return parsed
