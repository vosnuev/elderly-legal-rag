from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from external.openrouter import create_openrouter_chat_model
from query.read.inspection import list_chunks_for_document
from query.utils import node_properties
from tools import (
    check_document_unique_string_tool,
    read_document_tool,
    write_chunk_tool,
)

SYSTEM_PROMPT = """
You are chunking_agent for SKN28 RAG graph ingest.

Create semantic chunks from the original document without paraphrasing source text.
Each chunk must be copied from the original document, not summarized as replacement text.
For each chunk, assign tags, a short summary, and the reason for the boundary.
Read the source document through read_document_tool before chunking.
Use check_document_unique_string_tool repeatedly to make start_unique_string and
end_unique_string that each occur exactly once in the original document.
Use write_chunk_tool for final chunk persistence. The write tool generates chunk ids.
Never invent chunk ids.
After write_chunk_tool succeeds, briefly report that the chunks were stored.
"""


class ChunkingAgent:
    def tools(self) -> list[BaseTool]:
        return [
            read_document_tool,
            check_document_unique_string_tool,
            write_chunk_tool,
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

    def run(self, *, job_id: str, document_id: str) -> list[str]:
        tools = self.tools()
        agent = self.create_agent(tools)
        if agent is None:
            raise RuntimeError(
                "chunking_agent requires RAG_OPENROUTER_API_KEY and RAG_GRAPH_LLM_MODEL."
            )

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Create semantic chunks for this document_id. "
                            "Call read_document_tool first, then verify boundary "
                            "markers with check_document_unique_string_tool. "
                            "Persist chunks through write_chunk_tool using this "
                            "same document_id. Do not provide chunk ids yourself.\n"
                            f"document_id={document_id}"
                        ),
                    }
                ]
            }
        )
        _ = result
        chunk_ids = _stored_chunk_ids(document_id=document_id, job_id=job_id)
        if not chunk_ids:
            raise ValueError("chunking_agent did not write any chunks.")
        return chunk_ids


def _stored_chunk_ids(*, document_id: str, job_id: str) -> list[str]:
    result = list_chunks_for_document(document_id)
    chunk_ids: list[str] = []
    for row in result["rows"]:
        chunk = node_properties(row["chunk"])
        if job_id and str(chunk.get("last_ingest_job_id") or "") != job_id:
            continue
        chunk_id = str(chunk.get("id") or "").strip()
        if chunk_id:
            chunk_ids.append(chunk_id)
    return chunk_ids
