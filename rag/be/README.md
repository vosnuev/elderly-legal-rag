# RAG Backend

FastAPI 기반 RAG backend입니다. 문서 ingest API, external read-only MCP endpoint, internal agentic graph ingest runtime, Memgraph query business logic을 포함합니다.

## Runtime

- Python 3.13
- FastAPI
- FastMCP / MCP Streamable HTTP
- LangGraph pipeline for agentic ingest
- LangChain tools for internal graph ingest subagents
- OpenRouter-compatible LangChain chat/embedding clients via `src/external/openrouter/`
- Memgraph via Neo4j-compatible Bolt driver
- Pydantic / pydantic-settings

## Layout

```text
be/
├── src/app.py                  # FastAPI bootstrap and MCP mount
├── src/api/                    # MCP, ingest command, and FE operations API surfaces
├── src/pipeline/               # LangGraph ingest pipeline, subagents, and service nodes
├── src/external/memgraph/      # Pure Memgraph Bolt adapter
├── src/external/openrouter/    # OpenRouter chat and embedding client adapters
├── src/ingest_tasks/           # Document DB upload, ingest job state, task queue boundary
├── src/logger.py               # Loguru structured logging setup
├── src/query/                  # Memgraph read/write query functions
├── src/tools/                  # Singleton LangChain tools and context binding
├── src/settings.py             # Environment settings
├── tests/
├── .env.example
├── pyproject.toml
└── uv.lock
```

## Run

```bash
uv sync
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8010
```

## API

API code is split by boundary:

- `src/api/mcp/`: external read-only MCP server.
- `src/api/ingest/`: document ingest job creation and pipeline start commands.
- `src/api/operations/`: FE operations endpoints for status, documents, and search.

- `GET /health`
- `GET /api/system/dependencies`
- `POST /ingest`
- `GET /ingest/status/{job_id}`
- `POST /search`
- `POST /api/ingest/jobs`
- `GET /api/ingest/jobs/{job_id}`
- `POST /api/ingest/jobs/{job_id}/start`
- `GET /api/documents`
- `POST /api/documents/search`
- `GET /api/review/edge-candidates`
- `POST /api/review/edge-candidates/{candidate_id}/decision`

## Query Layer

`src/query/` is a direct function layer over Memgraph query primitives. It does
not contain prompt text, MCP instructions, repository abstractions, or a service
singleton.

- `src/query/read/`: raw read Cypher, schema reads, text search, vector search,
  bounded graph traversal, and document lookup by id.
- `src/query/write/`: raw write Cypher and deterministic original-document
  registration.
- `src/external/memgraph/`: pure Memgraph Bolt driver lifecycle and result
  serialization.

## MCP

External read-only MCP endpoint:

```text
http://127.0.0.1:8010/mcp
```

External MCP tools:

- `memgraph.read_query`
- `memgraph.vector_search`
- `memgraph.text_search`
- `memgraph.graph_traverse`
- `memgraph.schema_read`

MCP only exposes read tools. Internal ingest subagents import singleton
read/write tools from `src/tools/`; runtime context is bound in-process and is
not part of the LLM-facing tool schema.

## Ingest Flow

1. API receives text/file input.
2. `src/ingest_tasks/` stores the original document in Memgraph and creates an ingest job with `document_id`.
3. `IngestTaskQueue` starts the LangGraph pipeline with `job_id` and `document_id`.
4. `src/pipeline/invocation.py` invokes graph flows under `src/pipeline/graphs/`.
5. `chunking_agent` writes chunks through `write_chunk_tool`; `graph_candidate_agent` writes relationship candidates through `write_relationship_candidate_tool`.
6. Deterministic services persist embeddings, progress, review status, reviewer notes, and approved actual edge materialization.
7. Review APIs resume pending candidate decisions.

## Environment

- Example file: `.env.example`
- Local file: `.env` (do not commit)
- Settings prefix: `RAG_`
- Text search indexes are configured with `RAG_TEXT_SEARCH_INDEX_NAME`, `RAG_DOCUMENT_TEXT_SEARCH_INDEX_NAME`, and `RAG_REVIEW_NOTE_TEXT_SEARCH_INDEX_NAME`.
- Structured logs use Loguru. `RAG_LOG_JSON=true` emits JSON logs to stderr.

## Checks

```bash
PYTHONPATH=src uv run python -m unittest discover -s tests
PYTHONPATH=src uv run python -m compileall src tests
```
