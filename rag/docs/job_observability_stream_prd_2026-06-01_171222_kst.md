# Job Observability Stream PRD

Created: 2026-06-01 17:12:22 KST

## 1. Executive Summary

### Problem Statement

The RAG FE now has a Graph Jobs diagnostics modal, but the backend does not yet
provide a real job-scoped transparency stream. Operators can see a job card, but
they cannot inspect queue movement, worker execution, pipeline sequence,
service-node events, agent messages, token chunks, or tool-call events for that
specific `job_id`.

### Proposed Solution

Add a Redis-backed observability stream for every long-running document job.
Workers and pipeline nodes publish structured events to Redis Streams, and
FastAPI exposes a job-scoped SSE endpoint that reads Redis and forwards events
to the FE transparency monitor.

This is observability infrastructure, not the durable task queue. Task execution
may remain in-process for now; Redis is introduced first as the job event stream
and replay buffer.

### Success Criteria

- Opening the Graph Jobs diagnostics modal for a `job_id` receives live SSE
  events from `GET /api/ingest/jobs/{job_id}/events`.
- The FE can render the active topology node/edge for document registration,
  queue handoff, chunking, embedding dispatch, candidate generation, review
  revision/materialization, and completion.
- Queue backlog and worker load are emitted at least once per task state change.
- Agent events include visible assistant message tokens, tool call start/end,
  tool arguments, sanitized tool results, and agent-visible diagnostic summaries.
- Backend never emits hidden chain-of-thought; any FE `thought` field must be an
  explicit visible diagnostic note or summary.
- Redis Stream replay supports reconnect from the last event id for a selected
  job.

## 2. User Experience & Functionality

### User Personas

- RAG operator: uploads documents and monitors whether background processing is
  moving or blocked.
- Graph quality reviewer: uses job history to understand how candidates were
  created before approving or rejecting them.
- Backend developer: debugs worker, pipeline, service, and agent behavior
  without tailing local process logs.
- Demo stakeholder: watches a transparent end-to-end run in the FE diagnostics
  modal.

### User Stories

#### Story 1: Job-Scoped Transparency Modal

As a RAG operator, I want to click a document job and see live pipeline
progress so that I know where the job is currently executing.

Acceptance Criteria:

- FE opens an EventSource connection for the selected `job_id`.
- Events contain `job_id`, Redis stream event id, channel, timestamp, and
  payload.
- FE can highlight the active topology node and edge from event payload fields.
- If no live event arrives within a short timeout, FE may fall back to its demo
  simulator, but live stream must replace it once connected.

#### Story 2: Queue And Worker Visibility

As a RAG operator, I want to see queue backlog and worker load so that I can
distinguish waiting jobs from running jobs.

Acceptance Criteria:

- A queued task emits `worker_metrics` with `queue_count` and `worker_load`.
- A worker pickup emits lifecycle events for task start.
- Task success and failure emit lifecycle events with terminal status.
- Queue metrics are job-scoped but may also include global lane metrics.

#### Story 3: Pipeline Sequence Visibility

As a RAG operator, I want to see the processing sequence for the selected job so
that the graph construction flow is understandable.

Acceptance Criteria:

- Backend maps internal pipeline events to FE topology ids:
  - `document_constructed`
  - `task_queue`
  - `chunking_agent`
  - `embedding_dispatch`
  - `graph_candidate_agent`
  - `candidate_revision_agent`
  - `edge_materializer`
  - `completed`
- Events include the current `stage` and, when applicable, the active `edge`.
- Service nodes emit concise service logs.
- Agent nodes emit agent name, visible token/message events, tool call events,
  and sanitized tool result summaries.

#### Story 4: Review Decision Observability

As a graph quality reviewer, I want review decisions to have their own event
trail under the same job so that I can understand how a candidate was approved,
rejected, or retried.

Acceptance Criteria:

- Review task events use the existing candidate `job_id`.
- Review events are not represented as a new document job.
- Retry events show candidate revision activity.
- Approval events show edge materialization activity.

#### Story 5: Developer Replay And Debugging

As a backend developer, I want Redis to retain recent job event history so that
I can reconnect or inspect a failed job after the initial stream disconnects.

Acceptance Criteria:

- Redis stream keys are deterministic by `job_id`.
- SSE supports a `Last-Event-ID` header or equivalent query parameter.
- Stream length is bounded by configuration to avoid unbounded Redis growth.
- Event payloads are JSON and can be inspected with Redis CLI.

### Non-Goals

- FE does not connect directly to Redis.
- Redis is not introduced as the durable worker queue in this PRD.
- This PRD does not replace the existing Memgraph job progress storage.
- This PRD does not expose model hidden chain-of-thought.
- This PRD does not implement full LangGraph checkpointing.
- This PRD does not require WebSocket; SSE is the primary transport.

## 3. AI System Requirements

### Tool Requirements

- Redis Streams for job event append/replay.
- FastAPI SSE endpoint for browser delivery.
- Pipeline/worker publisher interface for lifecycle, service, agent, token, and
  tool events.
- Event sanitizer for agent/tool payloads.
- FE EventSource integration replacing the current WebSocket/demo connector.

### Event Categories

- `lifecycle`: task queued, worker assigned, task running, task succeeded, task
  failed.
- `service`: deterministic node activity such as document registration,
  embedding dispatch, progress update, review status update, and edge
  materialization.
- `agent`: visible agent message tokens, agent-visible diagnostic summaries, and
  tool-call lifecycle.
- `message`: general runtime messages that are not tied to a service or agent.
- `error`: exception and failure summaries.
- `worker_metrics`: queue count, worker load, lane name, and active task counts.

### Evaluation Strategy

- Use a fake pipeline publisher to emit every event category and verify FE can
  render the diagnostics modal without simulator fallback.
- Verify stream replay by reconnecting with the last Redis stream id and
  receiving only newer events.
- Verify sanitizer behavior with tool arguments/results containing long text,
  raw document content, secrets, or large embeddings.
- Verify hidden chain-of-thought is not emitted by checking event payload fields
  and agent transcript mapping.

## 4. Technical Specifications

### Architecture Overview

```text
worker / pipeline
  -> observability.consume.service
  -> observability.redis
  -> external.redis.client
  -> Redis Stream: rag:observability:jobs:{job_id}:events

FastAPI endpoint
  -> observability.expose.sse
  -> observability.events.ports.ObservabilityReader
  -> observability.redis
  -> XREAD job stream
  -> text/event-stream
  -> FE EventSource
```

Redis is the event bus and replay buffer. FastAPI remains the only browser-facing
stream endpoint.

### Backend Package Boundaries

```text
rag/be/src/external/redis/
└── client.py
    - redis.asyncio client factory
    - configured by RAG_REDIS_URL

rag/be/src/observability/
├── logger.py
│   - Loguru process logger setup and binding
├── redis.py
│   - Redis Stream XADD/XREAD implementation
├── consume/
│   ├── context.py
│   │   - job_id/task_id/kind context binding for runtime emitters
│   └── service.py
│       - thin observer facade used by worker/pipeline/agent code
├── expose/
│   └── sse.py
│       - SSE serialization helper for API routes
├── events/
│   ├── models.py
│   │   - event envelope and channels
│   └── ports.py
│       - publisher/reader interfaces

rag/be/src/knowledge_runtime/
├── application/
│   - document job submit
│   - review decision submit
│   - status read use cases
├── runtime/
│   - task queue
│   - worker pool
│   - pipeline runner
├── records/
│   - job/task state models and stores
└── documents/
    - document registration and catalog projection
```

### API Contract

Existing API surface remains the initial contract:

- `POST /api/ingest/jobs`
  - Create document job and submit build task.
- `GET /api/ingest/jobs/{job_id}`
  - Return job snapshot and current task snapshot.
- `POST /api/ingest/jobs/{job_id}/start`
  - Idempotent manual build task submission.
- `GET /api/ingest/jobs/{job_id}/events`
  - SSE stream for job observability.
- `GET /api/review/edge-candidates`
  - Pending review candidates.
- `POST /api/review/edge-candidates/{candidate_id}/decision`
  - Submit review task under the candidate's existing `job_id`.

### Redis Integration

Use `redis-py` asyncio:

- Connect with `redis.asyncio.from_url(settings.redis_url)`.
- Publish events with `XADD`.
- Read events with `XREAD`.
- Use bounded stream length with approximate trimming.

Proposed settings:

```text
RAG_REDIS_URL=redis://127.0.0.1:6379/0
RAG_OBSERVABILITY_STREAM_PREFIX=rag:observability:jobs
RAG_OBSERVABILITY_STREAM_MAXLEN=2000
RAG_OBSERVABILITY_XREAD_BLOCK_MS=15000
```

### Redis Key Design

```text
rag:observability:jobs:{job_id}:events
```

Each entry stores a JSON payload field:

```json
{
  "job_id": "job-123",
  "channel": "agent_transcript",
  "timestamp": "2026-06-01T17:12:22+09:00",
  "payload": {
    "stage": "chunking_agent",
    "edge": "chunk_to_embed",
    "type": "agent",
    "log": "Created semantic chunk proposal.",
    "agentName": "ChunkingAgent",
    "diagnosticNote": "Visible summary generated by the agent.",
    "toolUsage": {
      "name": "write_chunk_tool",
      "arguments": {
        "document_id": "doc-123",
        "chunk_index": 0
      },
      "result": "chunk_id=chunk-123"
    }
  }
}
```

For FE compatibility, the API may also emit `payload.thought`, but that value
must be copied from `diagnosticNote` and must never contain hidden reasoning.

Worker metrics entry:

```json
{
  "job_id": "job-123",
  "channel": "worker_metrics",
  "timestamp": "2026-06-01T17:12:22+09:00",
  "payload": {
    "queue_count": 2,
    "worker_load": 67,
    "lane": "build",
    "active_tasks": 1
  }
}
```

### FE Integration

Replace the current WebSocket connector in `use-event-streamer.ts` with
EventSource:

```text
GET {RAG_API_BASE_URL}/api/ingest/jobs/{job_id}/events
```

The hook should:

- open a connection only when a job is selected;
- parse SSE `data` as JSON;
- update topology node/edge from `payload.stage` and `payload.edge`;
- append terminal logs from `payload.log`;
- update queue/worker metrics from `worker_metrics`;
- keep simulator fallback only when SSE fails or backend is unavailable.

### Infrastructure

Add Redis to `rag/infra/docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  container_name: ${REDIS_CONTAINER_NAME:-rag-redis}
  ports:
    - "${REDIS_PUBLISH_HOST:-127.0.0.1}:${REDIS_PORT:-6379}:6379"
  volumes:
    - redis_data:/data
  command: ["redis-server", "--appendonly", "yes"]
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Add `redis_data` to the compose volumes.

### Security & Privacy

- Do not stream full raw document text by default.
- Redact environment variables, API keys, credentials, and authorization
  headers from tool arguments/results.
- Limit event payload size.
- Summarize long tool results.
- Do not emit embeddings or large vector arrays.
- Do not emit hidden model reasoning. Only visible tokens, tool events, service
  events, and explicit diagnostic summaries are allowed.

## 5. Risks & Roadmap

### Phased Rollout

#### MVP

- Add Redis service to `rag/infra`.
- Add `external/redis` client.
- Add observability publisher/reader using Redis Streams.
- Add job SSE endpoint.
- Emit task lifecycle and worker metrics events.
- Update FE hook from WebSocket to EventSource.

#### v1.1

- Bridge pipeline service-node events into the observability publisher.
- Bridge agent visible message/token stream and tool call events.
- Add payload sanitizer and max payload guard.
- Add reconnect/replay support using Redis stream ids.

#### v2.0

- Add Redis consumer groups or a dedicated observability worker if fanout grows.
- Add persisted event search/filtering for failed job analysis.
- Add per-node duration metrics and timeline summaries.
- Evaluate moving task queue durability behind Redis separately from
  observability.

### Technical Risks

- Event volume can grow quickly during token streaming; payload size and stream
  max length must be enforced.
- Redis outage can remove live transparency; workers should continue core job
  execution and log publisher failures.
- SSE connection limits can matter with many open diagnostics modals.
- Agent transcript mapping can accidentally expose hidden reasoning if not
  explicitly constrained.
- Long tool results can leak raw source text or large database payloads without
  sanitizer rules.

### Open Decisions

- Exact Redis event retention policy: default proposed max length is 2,000
  events per job stream.
- Whether queue backlog should be lane-global or filtered to selected job only.
- Whether token events should stream every token or be buffered into small
  chunks for UI performance.
- Final FE field name for visible diagnostic summaries: `diagnosticNote` is
  preferred, while `thought` may remain as a compatibility alias.
