# API Boundary

`api/`는 HTTP와 MCP 노출만 담당한다. 실제 문서 처리, graph construction,
Memgraph query 구현은 각각 `ingest_tasks/`, `pipeline/`, `query/`,
`external/`에 둔다.

## API Surface

```text
api/
├── router.py       # FastAPI HTTP router aggregator
├── mcp/            # 외부 agent가 사용하는 read-only MCP server
├── ingest/         # 문서 ingest job lifecycle 및 graph ingest 진행 command
└── operations/     # FE 운영 UI가 사용하는 조회성 API
```

`app.py`는 `api.router.api_router` 하나만 `include_router()`로 등록한다.
FastMCP는 FastAPI router가 아니므로 `api/mcp`에서 server를 만들고 `app.py`가
별도 ASGI app으로 mount한다.

## Directory Responsibilities

### `api/router.py`

- FastAPI HTTP endpoint aggregator이다.
- `api.ingest.router`, `api.operations.router`만 include한다.
- MCP server는 include하지 않는다.

### `api/mcp`

- FastMCP server를 생성한다.
- 외부에는 read-only Memgraph tool만 노출한다.
- write tool, internal pipeline tool, document ingest command는 노출하지 않는다.
- `app.py`가 `settings.external_mcp_path`에 mount한다.

### `api/ingest`

- 문서 ingest command surface이다.
- 원문 text/file 입력을 job으로 만들고 원문 문서를 database에 먼저 등록한다.
- ingest job status/progress 조회도 ingest job lifecycle에 속하므로 이 surface에 둔다.
- 사용자가 start graph add를 누르면 pipeline start command를 `ingest_tasks`로 넘긴다.
- candidate review 조회와 approve/reject/retry decision도 pending graph construction을
  다음 단계로 진행시키는 ingest action이므로 이 surface에 둔다.
- API가 직접 pipeline node를 실행하지 않고 `ingest_tasks -> queue -> pipeline`
  경계를 탄다.

```text
api/ingest/
├── router.py    # ingest HTTP router aggregator
├── jobs.py      # document upload/create/status/start endpoints
└── review.py    # relationship candidate review endpoints
```

### `api/operations`

- RAG 운영 FE가 보는 조회성 API surface이다.
- 현재 database에 올라간 document 목록과 document search를 제공한다.
- system health/dependency 조회를 제공한다.
- ingest job status/progress 조회는 FE에서 사용하더라도 `api/ingest` 소유이다.
- ingest pipeline을 진행시키는 command endpoint는 `api/ingest`에 둔다.

```text
api/operations/
├── router.py     # operations HTTP router aggregator
├── documents.py  # stored document list/search endpoints
├── search.py     # legacy search compatibility endpoint
└── health.py     # health/dependency endpoints
```

## Worker Boundary

현재 worker boundary는 process-internal이다.

```text
API
  -> ingest_tasks
      -> document_service / job_store / queue
          -> pipeline
              -> sub_agents
              -> services
              -> tools
                  -> query/read, query/write
                      -> external/memgraph
```

나중에 실제 task queue나 worker process를 붙일 경우 `ingest_tasks/queue.py`를
외부 queue adapter로 교체하고, API와 pipeline 내부 코드는 그대로 두는 방향이
현재 boundary의 목적이다.
