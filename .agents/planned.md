# Planning Log

## 2026-06-01 KST - RAG Worker Pool / Job Submission Flow

### Goal

Implement the RAG backend worker submission layer before refining API/FE contracts.

### Current State

- `rag/be/src/pipeline/invocation.py` already exposes two graph entry points:
  `start_construction(job_id, document_id)` and `apply_review_decision(candidate_id, action, reviewer, note)`.
- `rag/be/src/ingestion/dispatcher.py` currently calls those graph entry points synchronously.
- Existing graph split is intentional because human review happens between construction and review action.
- A single ingest `job_id` owns both graph task types.

### Approved Plan

- Add worker/submission modules under `rag/be/src/ingestion/`.
- Model two graph task kinds: `construction` and `review_action`.
- Use separated worker lanes:
  - construction worker count default: 1
  - review-action worker count default: 2
  - queue max size configurable through settings
- Construction idempotency key: `construction:{job_id}`.
- Review action idempotency key: `review:{job_id}:{candidate_id}`.
- Do not create a new job for review actions; they are tasks inside the existing ingest job.
- Keep pipeline/agent internals intact and call only through `GraphIngestInvocation`.
- Start/stop the pool from FastAPI lifespan.
- API routes should continue calling the ingestion service, not the worker pool directly.

### Approval Status

Approved by user for implementation.

## 2026-06-04 KST - Integrated Docker Compose and Backend RAG MCP Connection

### Goal

Create a root `infra/` Docker Compose workflow that runs the runnable app
services together, injects service env files from `infra/`, and verifies that
the main backend agent can call the RAG backend's external MCP tools over the
Compose network.

### Current State

- Branch is `feature/rag-red-team-neo4j-mcp`.
- The working tree already has many unrelated modified/deleted/untracked files;
  do not revert or sweep them into this task.
- `instructions.md` is referenced by AGENTS notes but is intentionally ignored
  and absent in the project root.
- `frontend/` has only README, `.gitignore`, and `.env.example`; there is no
  runnable app or package manifest there yet.
- Runnable app services found:
  - `backend/`: FastAPI main agent orchestrator, existing Dockerfile and
    `docker-compose.yml`.
  - `streamlit/`: Streamlit consultation UI, uv Python project.
  - `rag/be/`: FastAPI RAG backend with FastMCP Streamable HTTP mounted at
    `RAG_EXTERNAL_MCP_PATH`, default `/mcp`.
  - `rag/fe/`: Bun + Vite + React RAG operations UI.
- Supporting infra found:
  - `rag/infra/docker-compose.yml` runs Memgraph, Memgraph Lab, and Redis.
- Backend already has `langchain-mcp-adapters` and `BACKEND_RAG_MCP_URL`, but
  `backend/src/agent/tool.py` still returns placeholder/mock tools.
- `backend/src/agent/tool.py` currently defines `mock_policy_search_tool`
  twice; avoid expanding this duplication while wiring MCP tools.
- RAG backend external MCP tools are read-only:
  `memgraph.read_query`, `memgraph.vector_search`,
  `memgraph.text_index_search`, `memgraph.graph_traverse`,
  `memgraph.schema_read`.
- Context7/current local package check:
  - installed `langchain-mcp-adapters` is `0.2.2`.
  - `MultiServerMCPClient.get_tools()` is async.
  - Streamable HTTP accepts `transport` values `http`, `streamable_http`, and
    `streamable-http`; prefer `http` to match current docs examples.
- Current machine is `arm64`; Docker 29.0.1 and Docker Compose 5.1.1 are
  installed.
- Manifest checks show `memgraph/memgraph-mage:latest`,
  `memgraph/lab:latest`, `python:3.13-slim`, and `oven/bun:1-alpine` include
  linux/arm64 images.

### Env State

- `backend/.env` exists and uses `OPENROUTER_API_KEY`; settings accept this as
  an alias for `BACKEND_OPENROUTER_API_KEY`.
- `backend/.env` is missing several example keys, mostly optional service
  metadata, host publish settings, OpenRouter metadata/base URL defaults, and
  optional LangSmith tracing keys.
- `streamlit/.env` matches `streamlit/.env.example` by key.
- `rag/be/.env` exists and includes `RAG_OPENROUTER_API_KEY` and
  `RAG_FIRECRAWL_API_KEY` keys, but is missing some newer example keys for
  Firecrawl timeout/limits and worker queue tuning. Code has defaults for those.
- `rag/fe/.env` matches `rag/fe/.env.example` by key.
- `rag/infra/.env` exists but is missing Redis env keys from its example.
- `frontend/.env` is missing, but `frontend/` currently has no runnable app.
- `rag-red-team/.env` is missing; treat this as separate experimental Neo4j
  work unless the user confirms it belongs in this integration.

### User Comments

- Do not run `docs_web`.
- Put service-specific copied env files under root `infra/`, e.g.
  `.env_backend`.
- Compare actual `.env` files with `.env.example`; report missing/API-key
  requirements before relying on them.
- Build/run the services together in Docker, keep them on one network, and pick
  non-conflicting ports.
- Make the main backend agent use the RAG MCP server exposed by the RAG backend.
- Verify the connection from inside the Docker network using Docker commands.
- Use small/thin Linux containers but check compatibility issues.

### Proposed Plan

1. Confirm service scope before implementation.
   - Proposed runnable scope: `backend`, `streamlit`, `rag/be`, `rag/fe`.
   - Include infra dependencies: Memgraph, Memgraph Lab, Redis.
   - Exclude `docs_web`.
   - Exclude top-level `frontend/` for now because it has no runnable app.
   - Exclude `rag-red-team/` unless the user explicitly wants the separate
     Neo4j experiment included.

2. Prepare root `infra/` env layout.
   - Copy existing local env files into ignored root infra files:
     - `infra/.env_backend` from `backend/.env`
     - `infra/.env_streamlit` from `streamlit/.env`
     - `infra/.env_rag_be` from `rag/be/.env`
     - `infra/.env_rag_fe` from `rag/fe/.env`
     - `infra/.env_rag_infra` from `rag/infra/.env`
   - Add/refresh tracked examples or docs only, not real secrets.
   - Add missing non-secret defaults needed for Compose runtime:
     - backend MCP URL override: `http://rag-be:8010/mcp`
     - streamlit backend URL override: `http://backend:8000`
     - RAG BE Memgraph URL override: `bolt://memgraph:7687`
     - RAG BE Redis URL override: `redis://redis:6379/0`
     - RAG BE bind host override: `0.0.0.0`

3. Add thin Dockerfiles where missing.
   - Keep/adjust `backend/Dockerfile` only if needed.
   - Add `rag/be/Dockerfile` using `python:3.13-slim` + uv multi-stage.
   - Add `streamlit/Dockerfile` using `python:3.13-slim` + uv multi-stage.
   - Add `rag/fe/Dockerfile` using Bun build stage and a small static runtime
     such as nginx.
   - Add `.dockerignore` files for `rag/be`, `streamlit`, and `rag/fe` to keep
     `.env`, `.venv`, `node_modules`, `dist`, caches, and logs out of images.

4. Create root `infra/docker-compose.yml`.
   - One Compose network for all services.
   - Services:
     - `memgraph`
     - `memgraph-lab`
     - `redis`
     - `rag-be`
     - `backend`
     - `streamlit`
     - `rag-fe`
   - Proposed host ports:
     - backend: `127.0.0.1:8000` or configurable fallback `8001`
     - streamlit: `127.0.0.1:8501`
     - rag-be: `127.0.0.1:8010`
     - rag-fe: `127.0.0.1:5173`
     - Memgraph Bolt: `127.0.0.1:7687`
     - Memgraph Lab: `127.0.0.1:3000`
     - Redis: `127.0.0.1:6379`
   - Use `depends_on` with health checks where possible:
     - `rag-be` waits for Memgraph and Redis.
     - `backend` waits for `rag-be`.
     - UI services wait for their API dependencies where practical.

5. Wire backend MCP tools.
   - Replace placeholder RAG tool loading with `MultiServerMCPClient`.
   - Use connection config:
     - server name: `rag`
     - transport: `http`
     - URL: `settings.rag_mcp_url`
   - Because tool loading and MCP tool calls are async, convert chat execution
     to an async path:
     - load/cache tools through async startup or lazy async accessor.
     - use `agent.ainvoke()` and async stream APIs where supported.
     - update `api/chat.py` and tests accordingly.
   - Keep a controlled fallback behavior for startup when RAG MCP is not
     reachable only if needed for `/health`; do not silently pretend RAG worked
     during `/chat`.

6. Verify locally.
   - Run Python checks with uv:
     - `cd backend && uv run python -m compileall src scripts tests`
     - `cd backend && uv run python -m unittest discover -s tests`
     - `cd rag/be && uv run python -m compileall src tests`
     - focused RAG tests if they are not blocked by external services.
   - Run frontend checks:
     - `cd rag/fe && bun run build`
   - Build images:
     - `docker compose --env-file infra/.env -f infra/docker-compose.yml build`
   - Start stack:
     - `docker compose --env-file infra/.env -f infra/docker-compose.yml up -d`
   - Verify service health:
     - backend `/health`
     - rag-be `/health`
     - streamlit health endpoint
     - rag-fe HTTP response
     - Memgraph/Redis container health.
   - Verify MCP from Docker network:
     - run a one-off container or `docker compose exec backend ...` to list MCP
       tools from `http://rag-be:8010/mcp`.
     - call a read-only MCP tool such as `memgraph.schema_read`.
   - Verify backend agent path:
     - POST `/chat` from host and inspect backend logs/tool traces to confirm
       an MCP tool is available/called for a RAG-relevant prompt.

7. Update docs.
   - Update root `README.md` and `infra/README.md` with integrated Compose
     commands, service URLs, env-file layout, and troubleshooting.
   - Update service README files only where run commands or env behavior change.

### Open Questions

- Please confirm service scope: should the integrated app stack be exactly
  `backend`, `streamlit`, `rag/be`, and `rag/fe` plus Memgraph/Redis infra?
  This excludes top-level `frontend/` because it has no app yet.
- Should `rag-red-team/` be excluded from this stack? It is a separate Neo4j
  experiment and not the `rag/be` FastMCP endpoint currently consumed by the
  main backend.
- Host backend port preference: keep the existing Docker convention `8001`, or
  publish backend on `8000` so Streamlit/local docs align with the non-Docker
  command?

### Approval Status

Approved by user for implementation.

### Approval Notes

- Scope confirmed:
  - include `backend`, `streamlit`, `rag/be`, `rag/fe`.
  - exclude `rag-red-team/`; it is a separate Neo4j experiment.
  - exclude `docs_web`.
- Use the existing Docker Compose infra network currently named
  `infra_default`; existing Memgraph, Memgraph Lab, and Redis containers are
  already attached to it.
- The integrated compose should bring up all connected services in one command
  and attach them to the same infra network.
- Publish backend on host port `8100` to avoid conflicts; internal service port
  stays `8000`.

## 2026-06-01 KST - Knowledge Runtime Internal Service Split

### Goal

Implement the internal `knowledge_runtime` structure and split the API-facing service boundary into a `service/` package so one large service file does not accumulate all endpoint responsibilities.

### Current State

- `knowledge_runtime/` exists as a structure-only package.
- The old `ingestion` imports in API files are still broken and should not be repaired in this step.
- The user wants internal runtime structure first, with service responsibilities distributed by use case.

### Approved Plan

- Replace `knowledge_runtime/service.py` with `knowledge_runtime/service/`.
- Split service responsibilities into document work, review work, status/events, catalog, system, and runtime composition.
- Fill internal runtime models/stores/submitter/worker/event bus enough for the next API wiring step.
- Keep task words as `build` and `review`.
- Avoid adding a separate operation id.
- Do not run tests in this step unless the user asks later.

### Approval Status

Approved by user for implementation.

## 2026-06-01 KST - Knowledge Runtime Structure

### Goal

Replace the confusing deleted `ingestion` boundary with a clearer business/runtime package under `rag/be/src`.

### Current State

- The old `rag/be/src/ingestion/` files were deleted by the user and should not be restored.
- Existing API files still have broken legacy imports, but this step must not repair or rewire them.
- The user explicitly rejected `graph` / `ingest` naming for the new business layer.
- The immediate task is structure and responsibility documentation only, not tests or behavior wiring.

### Approved Plan

- Create `rag/be/src/knowledge_runtime/`.
- Use domain task words `build` and `review`.
- Keep `api/` as HTTP request/response only.
- Put document registration/catalog, job projection, task submit/state, worker lifecycle, runner adapter, and SSE event boundary under `knowledge_runtime/`.
- Do not introduce `operation_id`; tracking remains `job_id + task_id`.
- Do not run tests for this structure-only step.

### Approval Status

Approved by user for implementation.

## 2026-06-01 KST - RAG Worker Pool API Flow

### Goal

Make document add submit graph construction automatically and expose worker task tracking through job status responses.

### Current State

- `POST /api/ingest/jobs` currently creates a staged document/job response.
- `POST /api/ingest/jobs/{job_id}/start` currently submits the construction graph task.
- Worker execution already runs asynchronously through separated construction and review-action lanes.
- `FileIngestStatusResponse` does not expose task status to FE yet.

### Approved Plan

- Auto-submit `construction:{job_id}` after document registration in document add flows.
- Keep worker pool separated from API thread; API only submits to queue and returns status.
- Keep `POST /api/ingest/jobs/{job_id}/start` as an idempotent fallback/manual dispatch endpoint.
- Expose optional `current_task` in `FileIngestStatusResponse`.
- Use `job_id + task_id` for FE tracking; do not add `operation_id`.
- Return job status for review decision submission so FE sees the enclosing job and review-action task.
- Do not add durable queue or move directories in this step.

### Approval Status

Approved by user for implementation.

## 2026-06-01 KST - Knowledge Runtime State Ownership Cleanup

### Goal

Stabilize internal state ownership for the RAG knowledge build/review workflow.
The immediate issue is that job-level state such as `pending_review` is currently
produced around the pipeline graph boundary, while the actual business owner is
`knowledge_runtime`.

### Current State

- One document build workflow uses one `job_id`.
- The workflow is split into two graph executions:
  - document construction graph
  - candidate review graph
- `pipeline.state.GraphIngestState` is LangGraph runtime state. It is transient
  and should hold only values needed while a graph invocation is running.
- `RelationshipCandidate.status = pending_review` is the review queue source for
  FE candidate review.
- `IngestJob.phase = pending_review` is the job-level signal that construction
  completed and the system is waiting for user decision.
- `IngestJobNode.phase` is currently a plain `str`, so persisted job phase is not
  schema-protected.
- `ingest_progress_node_service` currently writes persisted job progress from
  inside the graph, which blurs pipeline execution with runtime job state
  ownership.
- `WorkerPool` should execute queued build/review tasks concurrently and manage
  task lifecycle/freeing, not own business state transitions.
- API wiring still references legacy `ingestion.service`, while the intended
  business/runtime boundary now lives under `knowledge_runtime`.

### User Comments

- This is a `knowledge_runtime` issue and should be fixed there.
- Internal state is unstable and should be split into value provider, modifier,
  and consumer roles.
- LangGraph internal state is temporary graph execution context and is not an
  appropriate owner for `pending_review`.
- The last construction graph node being `ingest_progress_node_service` is a sign
  that job state mutation is in the wrong layer.
- Worker pool should be understood as the concurrent execution owner, but its
  freeing/finish semantics need to be kept separate from job completion semantics.

### Proposed Plan

1. Define state ownership boundaries.
   - `pipeline`: creates graph artifacts and returns execution result only.
   - `knowledge_runtime`: owns job/task state transitions and persisted job
     progress updates.
   - `query`: provides primitive read/write operations and schema validation.
   - `api`: consumes projected status/review queue values only.

2. Split state roles in `knowledge_runtime`.
   - Provider:
     - job status projector
     - review queue reader
     - persisted progress reader
   - Modifier:
     - job progress modifier/finalizer
     - task lifecycle modifier
     - review decision submitter
   - Consumer:
     - API routes
     - FE-facing status response
     - worker metrics/event stream

3. Move job-level progress mutation out of pipeline graph nodes.
   - Remove graph-level `ingest_progress_node_service` from construction/review
     graph responsibility.
   - Keep graph return as an execution result with ids/counts/phase intent.
   - Add a `knowledge_runtime` job progress modifier that receives graph results,
     validates persisted DB state, and writes `IngestJob`.

4. Make pending review state deterministic.
   - Candidate-level pending state is created by candidate write query:
     `RelationshipCandidate.status = pending_review`.
   - Job-level pending state is created by `knowledge_runtime` after construction
     graph returns and persisted candidate count is checked.
   - If pending candidate count is greater than zero:
     `IngestJob.phase = pending_review`.
   - If no pending candidates remain after review actions:
     `IngestJob.phase = completed`.
   - FE can label `pending_review` as "Waiting for decision"; avoid adding a
     duplicate `waiting_for_decision` state unless the team explicitly wants a
     separate canonical phase.

5. Type persisted job phase.
   - Introduce an enum for persisted `IngestJob.phase` or reuse the runtime
     canonical job phase enum through query schema.
   - Replace `IngestJobNode.phase: str` with the enum type.
   - Keep graph phase and FE job phase mapping explicit.

6. Clarify worker pool semantics.
   - `WorkerPool` owns task queue state only:
     `queued -> running -> succeeded/failed`.
   - A build task can succeed while the job remains `pending_review`.
   - Worker freeing happens after graph result is handed to the job progress
     modifier and task success/failure is recorded.
   - Job completion is decided by the job progress modifier, not by worker queue
     availability.

7. Repair API wiring to `knowledge_runtime`.
   - Replace legacy `ingestion.service` API/app imports with
     `knowledge_runtime.service.knowledge_runtime`.
   - Keep routes thin: routes call runtime service methods and return projected
     responses.

### Open Questions

- Should `pending_review` remain the canonical persisted phase with FE display
  text "Waiting for decision"? Recommended: yes.
- Should `JobStore` remain an in-memory runtime cache, or should job progress be
  treated as Memgraph-backed source of truth immediately? Recommended: move
  durable job progress ownership to Memgraph and keep task queue state in memory
  for this iteration.

### Approval Status

Approved by user for implementation.
