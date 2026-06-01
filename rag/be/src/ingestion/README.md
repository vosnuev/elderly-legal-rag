# Ingestion

`ingestion/`은 HTTP API와 LangGraph pipeline 사이의 application/business
boundary이다. 이름에 `task`를 쓰지 않는 이유는 현재 구현이 외부 task queue가
아니라, 문서 등록과 job 상태 관리, pipeline dispatch를 묶는 상위 ingestion
use case 레이어이기 때문이다.

## 책임 한도

- FE/API 요청을 받아 ingest job을 생성한다.
- 원문 document를 먼저 Memgraph에 저장하고 `document_id`를 확보한다.
- job status와 stage response를 관리한다.
- `IngestionDispatcher`를 통해 `pipeline.invocation.GraphIngestInvocation`을 호출한다.
- pending relationship candidate review decision을 pipeline review graph로 전달한다.

## 하지 않는 것

- LangGraph node 내부 로직을 직접 구현하지 않는다.
- agent prompt나 tool schema를 소유하지 않는다.
- Memgraph query method를 직접 늘리지 않는다.
- MCP server를 만들지 않는다.
- 외부 SDK client를 직접 만들지 않는다.
- chunk/candidate DB schema를 정의하지 않는다.

## 디렉토리 구조

```text
ingestion/
├── service.py           # API-facing facade
├── dispatcher.py        # pipeline invocation dispatch boundary
├── document_service.py  # original document registration
├── job_store.py         # in-process ingest job state
├── schemas.py           # API/runtime DTOs
└── README.md
```

## 파일 역할

### `service.py`

API route가 호출하는 facade이다. document ingest job 생성, graph add 시작, candidate
review decision 적용처럼 FE/API가 요구하는 use case를 하나의 entry point로 묶는다.

이 파일은 API와 pipeline 사이의 경계를 정리한다. pipeline graph node를 직접 알거나
직접 실행하지 않고 `dispatcher.py`를 통해 호출한다.

### `dispatcher.py`

pipeline invocation boundary이다. 현재는 process-internal async/sync 호출 adapter에
가깝지만, 향후 실제 task queue나 worker pool이 붙으면 이 파일 뒤쪽에 queue adapter를
붙이는 방향이다.

### `document_service.py`

최초 원문 document를 Memgraph `Document` node로 등록한다. graph construction은
document가 먼저 저장되고 `document_id`가 확보된 뒤 시작된다.

이 단계는 agent가 아니라 deterministic service가 담당한다.

### `job_store.py`

현재 process 안에서 ingest job 상태와 stage response를 관리한다. production 수준의
worker queue나 durable job store가 붙기 전까지 FE가 진행 상태를 확인하기 위한
in-process store 역할을 한다.

### `schemas.py`

ingestion/API/job-facing DTO를 둔다. upload request, FE status response, ingest stage
enum처럼 API와 ingestion boundary에서 필요한 모델만 둔다. database graph node schema나
tool argument schema는 이 파일에 두지 않는다.

## 전체 플로우에서 위치

```text
api/ingest
  -> ingestion/service.py
      -> ingestion/document_service.py
      -> ingestion/job_store.py
      -> ingestion/dispatcher.py
          -> pipeline/invocation.py
```

`pipeline/`은 LangGraph graph 정의와 node 실행 흐름만 담당한다.
`ingestion/`은 pipeline node 내부 구현을 직접 알지 않고, `job_id`와
`document_id` 또는 review decision만 넘긴다.
