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
