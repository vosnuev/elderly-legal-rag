# API Boundary

`api/`는 HTTP와 MCP 노출만 담당한다. 실제 문서 처리, graph construction,
Memgraph query 구현은 각각 `ingest_tasks/`, `pipeline/`, `query/`,
`external/`에 둔다.

## 세 가지 API Surface

```text
api/
├── mcp/          # 외부 agent가 사용하는 read-only MCP server
├── ingest/       # 문서 ingest job 생성 및 worker/pipeline start command
└── operations/   # FE 운영 UI가 사용하는 상태/문서/review 조회 및 조작 API
```

### `api/mcp`

- FastMCP server를 생성한다.
- 외부에는 read-only Memgraph tool만 노출한다.
- write tool, internal pipeline tool, document ingest command는 노출하지 않는다.

### `api/ingest`

- 문서 처리 command surface이다.
- 원문 text/file 입력을 job으로 만들고, 사용자가 요청하면 pipeline start command를
  `ingest_tasks`로 넘긴다.
- API가 직접 pipeline node를 실행하지 않고 `ingest_tasks -> queue -> pipeline`
  경계를 탄다.

### `api/operations`

- RAG 운영 FE가 보는 상태, 문서 목록, 검색, pending review, review decision을
  처리한다.
- 조회성 endpoint와 HITL review action을 포함한다.
- review decision은 UI action이지만 내부적으로는 `GraphIngestPipeline.resume_review`
  를 직접 호출하지 않고 `ingest_tasks -> queue -> pipeline` 경계를 탄다.

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
