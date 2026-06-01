# Query Read Layer

`query/read/`는 Memgraph read query method만 담는다. MCP server, FastAPI route,
LangChain `@tool`, prompt, DTO 변환은 이 디렉토리 책임이 아니다.

## 구조

```text
read/
├── core/        # bounded Cypher read, SHOW SCHEMA INFO
├── discovery/   # text search, vector search, graph traversal
├── inspection/  # internal id-based graph state observation
└── runtime/     # API/ingestion status and review queue reads
```

## 책임 한도

- `core/`
  - Memgraph read transaction으로 Cypher를 실행한다.
  - Memgraph `SHOW SCHEMA INFO`를 호출한다.
  - document, chunk, candidate 같은 business 의미를 넣지 않는다.

- `discovery/`
  - Memgraph official text/vector search procedure를 호출한다.
  - bounded Cypher path traversal을 제공한다.
  - Python에서 graph traversal algorithm이나 combined hybrid search를 만들지 않는다.

- `inspection/`
  - internal agent와 non-LLM pipeline service가 DB state를 확인하는 계층이다.
  - document raw content, chunk list, candidate detail/version, review note,
    materialized edge, agent memory를 id 기준으로 읽는다.
  - external MCP에 기본 노출하지 않는다.

- `runtime/`
  - API/ingestion service가 document/job/review queue 상태를 읽는 계층이다.
  - FE DTO shape는 만들지 않고, API/ingestion layer가 응답 모델로 변환한다.

## 노출 규칙

- MCP: `core` + `discovery` subset만 FastMCP tool로 등록한다.
- Internal tools: agent 역할에 따라 `core`, `discovery`, `inspection`을 LangChain
  `@tool`로 감싼다.
- Pipeline services: LLM 없이 확인해야 하는 DB state는 `inspection`을 직접 import한다.
- API/ingestion: job/document/review status는 `runtime`을 import한다.

## 함수별 사용 시점

### `core/`

| 함수 | 언제 사용하는가 |
| --- | --- |
| `read_query` | agent 또는 MCP caller가 직접 Cypher read query를 작성해서 실행해야 할 때 사용한다. internal agent의 자유 탐색용 read tool과 external MCP `memgraph.read_query`의 기반이다. |
| `schema_read` | agent가 현재 Memgraph label, relationship, index 구조를 확인해야 할 때 사용한다. external MCP `memgraph.schema_read`, feedback judge, graph candidate agent의 schema 확인에 사용한다. |

### `discovery/`

| 함수 | 언제 사용하는가 |
| --- | --- |
| `text_search` | 법령명, 조례명, 조문 번호, 지역명, 기관명처럼 Memgraph text index 기반 anchor를 찾을 때 사용한다. MCP에는 혼동을 줄이기 위해 `memgraph.text_index_search`로 노출한다. substring `CONTAINS` scan은 `read_query`로 직접 작성한다. internal graph candidate discovery, reviewer note search wrapper의 기반이다. |
| `text_search_edges` | edge property에 text index가 잡혀 있고, 승인된 relationship metadata나 edge evidence를 text로 찾아야 할 때 사용한다. 기본 MCP surface에는 당장 노출하지 않고, edge index가 준비된 뒤 내부/외부 wrapper에서 선택적으로 감싼다. |
| `vector_search` | 새 chunk와 의미적으로 가까운 기존 node/chunk/entity를 찾을 때 사용한다. graph candidate agent가 기존 graph placement 후보를 찾는 검색 단계와 MCP `memgraph.vector_search`의 기반이다. |
| `vector_search_edges` | edge embedding index가 준비되어 있고, 기존 relationship 자체와 의미적으로 유사한 edge를 찾아야 할 때 사용한다. edge vector index가 없는 환경에서는 호출하면 Memgraph procedure/index error가 그대로 드러나야 한다. |
| `graph_traverse` | 특정 node id를 anchor로 주변 graph neighborhood/path를 bounded depth로 확장할 때 사용한다. MCP `memgraph.graph_traverse`, internal agent의 주변 context 확인, `inspection.read_node_neighborhood`의 기반이다. |

### `inspection/`

`inspection`은 내부 관찰 계층이다. LLM agent와 non-LLM pipeline service가 DB state를
확인할 때 사용하며, external MCP에 기본 노출하지 않는다.

| 함수 | 언제 사용하는가 |
| --- | --- |
| `read_node_by_id` | label을 알거나 모르는 graph node를 `id` 기준으로 정확히 읽어야 할 때 사용한다. candidate materialization, candidate review graph, agent tool 내부 검증의 기본 read이다. |
| `read_nodes_by_ids` | agent나 service가 여러 chunk/candidate/entity id 목록을 state로 들고 있고, DB에 실제 존재하는지 한 번에 확인할 때 사용한다. |
| `read_node_neighborhood` | internal agent/service가 node id 기준 주변 graph를 확인해야 하지만 MCP wrapper를 거치지 않을 때 사용한다. 내부적으로 `discovery.graph_traverse`를 사용한다. |
| `read_document_by_id` | graph construction 시작 전에 `Document` node가 존재하는지 확인할 때 사용한다. |
| `get_document_record` | 기존 callsite compatibility용 document read alias이다. document construction graph와 document service에서 사용한다. |
| `get_document_raw_content` | chunking agent가 `document_id`만 받은 뒤 원문을 읽어 chunk를 만들 때 사용한다. |
| `list_chunks_for_document` | document에서 생성된 chunk들이 DB에 저장됐는지, 다음 agent/service가 document 단위 chunk list를 대조해야 할 때 사용한다. |
| `read_chunk_by_id` | 특정 chunk id 하나의 text, marker, embedding status를 확인해야 할 때 사용한다. |
| `list_unembedded_chunks` | embedding dispatch service나 future worker가 아직 embedding 완료되지 않은 chunk를 찾아 처리할 때 사용한다. |
| `read_relationship_candidate` | review graph가 candidate decision을 적용하기 전에 candidate detail을 정확히 읽을 때 사용한다. |
| `list_candidates_for_job` | job 단위로 candidate 생성 결과, pending/rejected/approved 상태를 확인할 때 사용한다. |
| `list_candidates_for_document` | document에 연결된 chunk/evidence 기준으로 candidate를 다시 모아 document-level review 상태를 확인할 때 사용한다. |
| `list_candidate_versions` | 사용자가 request update/retry를 선택한 뒤 기존 candidate와 revised candidate version을 함께 확인할 때 사용한다. |
| `list_review_notes_for_candidate` | 특정 relationship candidate에 붙은 reviewer note를 읽어 retry/revision context로 사용할 때 사용한다. |
| `list_review_notes_for_job` | job 단위 feedback 기록을 모아 memory update agent 또는 review audit 화면에 전달할 때 사용한다. |
| `list_agent_memory` | graph candidate/revision agent가 반복되는 reviewer preference나 법령 계층 해석 rule을 읽을 때 사용한다. |
| `list_materialized_edges_for_candidate` | approve 이후 실제 edge가 생성됐는지, candidate provenance가 edge에 남았는지 확인할 때 사용한다. |

### `runtime/`

`runtime`은 API/ingestion service가 status와 review queue를 만들기 위해 사용하는 read
계층이다. FE DTO 변환은 여기서 하지 않고 API/ingestion layer에서 한다.

| 함수 | 언제 사용하는가 |
| --- | --- |
| `list_workspace_documents` | operations UI나 document API가 저장된 document 목록을 보여줘야 할 때 사용한다. |
| `list_documents` | 기존 callsite compatibility용 workspace document list alias이다. |
| `search_documents` | document API가 document text index 기반 검색을 제공해야 할 때 사용한다. |
| `read_ingest_job` | API/ingestion layer가 특정 job의 persisted `IngestJob` 상태를 읽어야 할 때 사용한다. |
| `summarize_job_progress` | job detail/status 화면에서 document count, candidate count, pending review count를 한 번에 계산해야 할 때 사용한다. |
| `list_pending_review_candidates` | review queue API가 pending relationship candidate 목록을 반환할 때 사용한다. document/job filter가 있으면 특정 document page나 job page의 review queue로 좁힌다. |
| `summarize_document_review_queue` | document page에서 chunk count, candidate count, pending count, candidate ids를 accordion/status summary로 보여줘야 할 때 사용한다. |
