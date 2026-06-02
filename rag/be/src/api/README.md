# API Boundary

`api/`는 HTTP와 MCP 노출만 담당한다. 실제 문서 작업 lifecycle,
Memgraph query 구현은 각각 `knowledge_runtime/`, `pipeline/`, `query/`,
`external/`에 둔다.

## 책임 한도

- FastAPI HTTP router를 구성한다.
- FastMCP server를 mount할 수 있는 MCP surface를 제공한다.
- FE가 호출하는 document job, status 조회, review decision endpoint를 제공한다.
- 개발/검증용으로 document 등록 후 chunking까지만 실행하는 preview endpoint를 제공한다.
- 외부 agent가 호출하는 read-only MCP endpoint를 제공한다.

## 하지 않는 것

- document를 직접 chunking하지 않는다.
- LangGraph pipeline node를 직접 구현하지 않는다.
- Memgraph query business logic을 구현하지 않는다.
- tool schema를 정의하지 않는다.
- OpenRouter/Memgraph SDK client를 직접 만들지 않는다.

## API Surface

```text
api/
├── router.py       # FastAPI HTTP router aggregator
├── mcp/            # 외부 agent가 사용하는 read-only MCP server
├── ingest/         # 기존 URL 호환용 document job/review command
└── operations/     # FE 운영 UI가 사용하는 조회성 API
```

`app.py`는 `api.router.api_router` 하나만 `include_router()`로 등록한다.
FastMCP는 FastAPI router가 아니므로 `api/mcp`에서 server를 만들고 `app.py`가
별도 ASGI app으로 mount한다.

## 디렉토리별 책임

### `api/router.py`

- FastAPI HTTP endpoint aggregator이다.
- `api.ingest.router`, `api.operations.router`만 include한다.
- MCP server는 include하지 않는다.

### `api/mcp`

- FastMCP server를 생성한다.
- 외부에는 read-only Memgraph tool만 노출한다.
- write tool, internal pipeline tool, document ingest command는 노출하지 않는다.
- `app.py`가 `settings.external_mcp_path`에 mount한다.

파일 역할:

- `server.py`: FastMCP server 생성과 read-only tool registration.

### `api/ingest`

- 기존 FE URL과 호환되는 document command surface이다.
- 원문 text/file 입력을 job으로 만들고 원문 문서를 database에 먼저 등록한다.
- job status/progress 조회도 같은 lifecycle에 속하므로 이 surface에 둔다.
- 사용자가 manual start를 누르면 `knowledge_runtime.service.documents`로 넘긴다.
- candidate review 조회와 approve/reject/retry decision도 `knowledge_runtime.service.reviews`
  로 넘긴다.
- API가 직접 pipeline node를 실행하지 않고 `knowledge_runtime -> pipeline`
  경계를 탄다.

```text
api/ingest/
├── router.py    # ingest HTTP router aggregator
├── debug.py     # document 등록 후 chunking_agent까지만 실행하는 preview endpoint
├── jobs.py      # document upload/create/status/start endpoints
└── review.py    # relationship candidate review endpoints
```

파일 역할:

- `router.py`: ingest 하위 router를 하나로 묶는다.
- `debug.py`: FE/개발자가 chunking_agent transcript와 chunk id 반환을 확인하는 preview endpoint.
- `jobs.py`: document upload, job creation, graph add start, job status 조회.
- `review.py`: pending edge candidate 조회와 approve/reject/retry decision 적용.

### `api/operations`

- RAG 운영 FE가 보는 조회성 API surface이다.
- 현재 database에 올라간 document 목록과 document search를 제공한다.
- system health/dependency 조회를 제공한다.
- job status/progress 조회는 FE에서 사용하더라도 `api/ingest` 소유이다.
- background work를 진행시키는 command endpoint는 `api/ingest`에 둔다.

```text
api/operations/
├── router.py     # operations HTTP router aggregator
├── documents.py  # stored document list/search endpoints
├── search.py     # legacy search compatibility endpoint
└── health.py     # health/dependency endpoints
```

파일 역할:

- `router.py`: operations 하위 router를 하나로 묶는다.
- `documents.py`: 저장된 document 목록과 document 조회.
- `search.py`: FE 검색 화면 또는 legacy compatibility용 search endpoint.
- `health.py`: service health와 dependency 상태 조회.

## Worker Boundary

현재 worker boundary는 process-internal이다.

```text
API
  -> knowledge_runtime
      -> service / documents / jobs / tasks / workers / events
          -> pipeline
              -> sub_agents
              -> services
              -> tools
                  -> query/read, query/write
                      -> external/memgraph
```

나중에 durable queue나 별도 worker process를 붙일 경우 `tasks.submitter`와
`workers.pool` 뒤에 queue adapter를 붙이고, API와 pipeline 내부 코드는 그대로
두는 방향이 현재 boundary의 목적이다.
