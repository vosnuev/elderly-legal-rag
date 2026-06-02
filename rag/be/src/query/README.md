# Query Layer

`query/`는 Memgraph database interaction만 담당하는 레이어이다.
agent 실행, MCP server, FastAPI route, prompt, task queue 상태 관리는 이
디렉토리 책임이 아니다.

## 책임 한도

- Memgraph에 Cypher query를 실행하기 위한 read/write 함수 제공.
- Memgraph node/relationship storage contract 정의.
- query parameter 정리, graph property 직렬화, node property 역직렬화.
- 내부 agent tool과 외부 MCP read tool이 공통으로 사용할 database query 함수 제공.

`query/`는 service singleton을 만들지 않는다. database connection singleton은
`external.memgraph.get_memgraph_bolt_client()`가 담당하고, 호출자는 필요한 query
function을 직접 import해서 사용한다.

## 하지 않는 것

- agent prompt를 두지 않는다.
- LangGraph node나 agent runner를 두지 않는다.
- MCP server wrapper를 두지 않는다.
- FastAPI router를 두지 않는다.
- job progress, worker status, retry policy를 관리하지 않는다.
- `dry_run`, mock execution branch를 query method에 넣지 않는다.
- `guard.py`, `instructions.py`, `repositories/`처럼 책임이 모호한 파일을 두지 않는다.

## 디렉토리 구조

```text
query/
├── __init__.py       # 외부 레이어가 import할 query function export
├── read/             # Memgraph read query methods
├── write/            # internal write query methods
├── schema/           # Memgraph storage schema contract
├── utils.py          # read/write 공통 query helper
└── README.md
```

## 파일 역할

### `read/`

read method는 database 조회 primitive이다. 내부 agent tool과 외부 MCP read tool이
둘 다 이 함수를 감쌀 수 있지만, 같은 surface를 공유하지 않는다. caller는 목적에 맞는
subpackage에서 필요한 read function만 import한다.

- `core/`: bounded read Cypher와 `SHOW SCHEMA INFO` 같은 lowest-level read.
- `discovery/`: Memgraph text search, vector search, bounded traversal.
- `inspection/`: 내부 agent와 pipeline service가 사용하는 id 기반 graph state 조회.
- `runtime/`: API/knowledge_runtime layer가 사용하는 document, job, review queue 상태 조회.

외부 MCP는 `core`와 `discovery`의 read-safe subset만 감싼다. 내부 LangChain tool은
필요할 때 `inspection`을 추가로 감쌀 수 있다. API/knowledge_runtime status flow는
`runtime`을 사용한다.

### `write/`

write method는 내부 runtime 전용이다. 외부 MCP로 노출하지 않는다.

- `core/`: raw write Cypher 실행 기반 함수.
- `documents.py`: graph construction 시작 전에 원본 `Document` 노드를 등록하고
  Memgraph `randomUUID()`로 생성한 `Document.id`를 `document_id`로 반환한다.
- `chunks.py`: `chunking_agent`가 만든 chunk payload를 `Chunk` node와
  `Document -[:HAS_CHUNK]-> Chunk` edge로 저장하고, Memgraph `randomUUID()`로
  생성한 `Chunk.id` 목록을 반환한다.
- `candidates.py`: `graph_candidate_agent`가 만든 relationship candidate를 실제
  `RelationshipCandidate` node와 review artifact link로 저장한다.
- `reviews.py`: candidate review status와 `ReviewNote`를 저장한다.
- `edges.py`: approved candidate를 실제 graph relationship으로 materialize한다.
- `embeddings.py`: chunk embedding vector와 status를 업데이트한다.
- `runtime.py`: `IngestJob` operational progress를 저장한다.

chunk 생성, edge candidate 생성, review note 생성은 agent tool 또는 pipeline service가
write query function을 호출해서 수행한다. 단, 최초 원문 document registration은
API/knowledge_runtime boundary에서 먼저 수행하는 deterministic write로 남긴다.

### `schema/`

Memgraph에 저장되는 node/relationship shape를 정의한다.

- `Document`
- `Chunk`
- `RelationshipCandidate` 또는 `EdgeCandidate`
- `ReviewNote`: `RelationshipCandidate`에 붙는 review artifact.
- `Memory`: review feedback을 누적한 단일 memory artifact.
- `IngestJob`: pipeline progress/status 조회용 operational node.
- materialized relationship metadata

tool argument schema는 이곳에 두지 않는다. tool argument schema는 `tools/` 안의
각 tool 파일에 둔다. 다만 tool schema는 이 DB schema를 기준으로 adapter/subset을
구성해야 한다.

### `utils.py`

read/write method에서 공유하는 작은 helper만 둔다.

- query limit bound
- Cypher identifier validation
- Memgraph DB-generated id expression
- Memgraph property serialization
- node property normalization

business logic, agent context, job id tracking은 이 파일에 넣지 않는다.

## 전체 플로우에서 위치

```text
api
  -> ingestion
      -> pipeline
          -> tools / services
              -> query/read, query/write, query/schema
                  -> external/memgraph
```

외부 MCP는 `query/read`만 감싼다. 내부 agent tool은 `query/read`와 `query/write`를
사용할 수 있다.

## Testing

read/write query layer 검증 절차는 [testing.md](./testing.md)를 따른다.
