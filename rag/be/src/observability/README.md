# Observability

`observability/` is the cross-cutting boundary for process logs and job
transparency. It separates runtime-facing consume APIs from API/FE-facing expose
adapters while hiding Redis details from workers, pipeline nodes, API routes,
and agent transcript code.

## Responsibility

- Provide a thin consume-side `ObservabilityService` for worker, pipeline, and
  agent code.
- Provide expose-side SSE helpers for API routes.
- Own process-wide logger setup through `observability.logger`.
- Publish job-scoped events to Redis Streams.
- Read job-scoped Redis Streams for SSE endpoints.
- Bind `job_id`, `task_id`, and task kind through context.
- Prevent Redis client imports from leaking into runtime or pipeline code.

## Directory Map

```text
observability/
├── logger.py          # process-wide Loguru setup and logger binding
├── redis.py           # Redis Streams XADD/XREAD implementation
├── consume/
│   ├── context.py     # job_id/task_id/kind context binding
│   └── service.py     # observer facade consumed by runtime/pipeline code
├── expose/
│   └── sse.py         # FastAPI StreamingResponse adapter
├── events/
│   ├── models.py      # event envelope and channel names
│   └── ports.py       # publisher/reader protocols
```

## Boundaries

Allowed to import `external.redis`:

- `observability/redis.py`

Not allowed to import `external.redis`:

- `api/`
- `knowledge_runtime/`
- `pipeline/`
- `tools/`

Runtime and pipeline code consume the observer facade:

```python
from observability.consume.service import observer

await observer.lifecycle(...)
await observer.service(...)
await observer.agent(...)
await observer.worker_metrics(...)
```

Use the logger boundary directly:

```python
from observability.logger import bind_logger, configure_logging
```

FastAPI status/event routes expose streams through the SSE adapter:

```python
from observability.expose.sse import observability_stream_response
```

## Redis Key

```text
{RAG_OBSERVABILITY_STREAM_PREFIX}:{job_id}:events
```

Default:

```text
rag:observability:jobs:{job_id}:events
```

## Event Channels

- `agent_transcript`: FE terminal log events for lifecycle, service, and agent
  output.
- `worker_metrics`: queue backlog, worker load, lane, and active task count.
- `lifecycle`, `service`, `error`: reserved channels for future non-FE
  consumers.

## Hidden Reasoning Rule

Do not publish hidden model chain-of-thought. If the FE needs a `thought` field,
it must be an explicit visible diagnostic summary, mirrored from
`diagnosticNote`.
