# RAG

Memgraph 기반 GraphRAG, 문서 ingest, MCP query tool, RAG 운영 UI를 관리하는 독립 서브시스템입니다.

## Layout

```text
rag/
├── be/            # FastAPI RAG backend, MCP, ingest task layer, graph ingest runtime
├── fe/            # Bun + Vite + React RAG operations UI
├── docs/          # PRD and architecture docs
├── infra/         # Memgraph and Memgraph Lab Docker Compose
├── sample_datas/  # Local sample text/JSON data
└── code_reference/ # Legacy/reference scripts kept out of runtime
```

## Services

### Backend

```bash
cd rag/be
uv sync
PYTHONPATH=src uv run uvicorn app:app --host 127.0.0.1 --port 8010
```

External read-only MCP endpoint:

```text
http://127.0.0.1:8010/mcp
```

Internal graph ingest subagents import singleton LangChain tools from
`rag/be/src/tools/`. Runtime job/document context is bound in-process and those
tools are not exposed through MCP.

### Frontend

```bash
cd rag/fe
bun install
bun run dev
```

Default FE URL:

```text
http://127.0.0.1:5173
```

Set `VITE_RAG_API_BASE_URL` in `rag/fe/.env` if the backend is not running on `http://127.0.0.1:8010`.

### Local Infra

```bash
cd rag
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

Default endpoints:

- Memgraph Bolt: `bolt://127.0.0.1:7687`
- Memgraph Lab: `http://127.0.0.1:3000`

## Docs

- `docs/memgraph_mcp_graphrag_prd.md`: Memgraph 기반 GraphRAG, MCP query server, 문서 ingest/그래프 확장 설계 PRD
- `docs/query_agent_tool_boundary_correction_prd.md`: query layer, subagent tool, Memgraph write ownership correction PRD
- `be/README.md`: Backend runtime, API, env, and test commands
- `infra/README.md`: Memgraph and Memgraph Lab Docker Compose usage
