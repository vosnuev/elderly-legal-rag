# Query Write Layer

`query/write/`는 Memgraph에 데이터를 저장하거나 갱신하는 Cypher query method만 담는다.
LangChain `@tool`, FastAPI route, MCP server, prompt, FE DTO는 이 디렉토리 책임이 아니다.

## 구조

```text
write/
├── core/          # raw Cypher write execution
├── documents.py  # original Document registration
├── chunks.py     # Chunk node + Document -> Chunk edge
├── candidates.py # RelationshipCandidate node + review artifact links
├── reviews.py    # candidate status and ReviewNote
├── memory.py     # 단일 Memory document versioned update
├── edges.py      # approved candidate -> actual graph edge
├── embeddings.py # Chunk embedding/status update
└── runtime.py    # IngestJob operational progress
```

## 책임 한도

- `core/`는 Memgraph write transaction 실행만 담당한다.
- `documents.py`는 최초 원문 저장만 담당한다. 이 단계는 agent가 아니라 knowledge runtime
  service가 수행한다.
- `chunks.py`와 `candidates.py`는 internal agent가 호출하는 write tool의 persistence
  backend이다. agent가 내용을 생성하고, write layer가 DB id 생성과 schema validation을
  담당한다.
- `candidates.py`는 `left_node`, `right_node`가 실제 DB에 존재할 때만 candidate를
  저장한다. `evidence_node_id`는 optional provenance anchor이며, 별도 문서/청크가
  관계를 언급했을 때만 link로 남긴다.
- `RelationshipCandidate.status`는 `query.schema.RelationshipCandidateStatus` enum으로
  검증한다.
- `reviews.py`, `edges.py`, `runtime.py`, `embeddings.py`는 non-LLM graph node/service가
  사용하는 DB write method이다.

## 노출 규칙

- MCP에는 write method를 노출하지 않는다.
- internal agent에는 `tools/`의 schema-aware write tool만 제공한다.
- service와 tool은 직접 Cypher를 만들지 않고 이 디렉토리의 함수만 호출한다.
- `write_query`는 내부 기반 함수이다. agent/MCP surface에 직접 노출하지 않는다.

## 함수별 사용 시점

| 함수 | 언제 사용하는가 |
| --- | --- |
| `write_query` | query/write 내부 구현이나 낮은 수준의 maintenance script가 직접 Cypher write를 실행해야 할 때 사용한다. |
| `register_document` | 사용자가 업로드한 원문을 graph construction 시작 전에 `Document` node로 저장하고 DB-generated `document_id`를 받을 때 사용한다. |
| `write_chunks_for_document` | `chunking_agent`가 만든 chunk payload를 저장하고 DB-generated `chunk_ids`를 받아야 할 때 사용한다. |
| `write_relationship_candidates` | `graph_candidate_agent`가 기존 graph와의 proposed edge를 `RelationshipCandidate` node로 저장할 때 사용한다. |
| `update_candidate_review_status` | review graph가 reject 상태를 candidate에 반영할 때 사용한다. approve는 edge materialization 단계가 같이 반영한다. |
| `store_review_note` | 사용자가 candidate review note를 남겼을 때 `ReviewNote` node로 저장할 때 사용한다. |
| `update_memory_document` | memory update agent가 현재 Memory와 job-level ReviewNote context를 종합해 단일 `Memory` 문서 전체를 갱신할 때 사용한다. |
| `materialize_candidate_edge` | approve된 `RelationshipCandidate`를 실제 graph relationship으로 반영할 때 사용한다. |
| `update_chunk_embedding` | embedding worker/service가 특정 chunk 하나의 embedding vector와 status를 업데이트할 때 사용한다. |
| `upsert_ingest_job_progress` | knowledge runtime job progress를 `IngestJob` operational node로 저장할 때 사용한다. |

## Future Improvements

### RelationshipCandidate duplicate handling

현재는 `RelationshipCandidate.id`를 저장 시점에 생성하고 이 id를 기준으로 `MERGE`한다.
관계에는 `relationship_direction`이 있으므로 `A -> B`와 `B -> A`를 단순한 unordered
pair로 항상 같은 후보라고 볼 수는 없다. 실제 edge 기준으로 중복을 판단하려면
`left_node/right_node`와 `relationship_direction`을 함께 해석해야 한다.

향후 candidate 중복이 실제 review queue 품질 문제로 확인되면 아래 방향을 검토한다.

- `left_to_right`, `right_to_left`, `bidirectional`을 반영해 실제 materialized source/target을
  계산한다.
- `job_id + normalized_relationship_type + actual_source_node + actual_target_node` 기반의
  deterministic candidate key를 만든다.
- `RELATED_TO`처럼 의미상 대칭인 관계 타입은 별도 taxonomy를 두고 unordered key 또는
  `bidirectional` 강제 규칙을 적용한다.
- query write layer에서 deterministic key로 `MERGE`하고, 가능하면 DB constraint/index를
  추가한다.

현재 단계에서는 `graph_candidate_agent`가 실제로 어떤 방향/관계 후보를 만드는지
관찰하는 것을 우선하며, 중복 최적화는 보류한다.
