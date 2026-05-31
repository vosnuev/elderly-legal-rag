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
├── edges.py      # approved candidate -> actual graph edge
├── embeddings.py # Chunk embedding/status update
└── runtime.py    # IngestJob operational progress
```

## 책임 한도

- `core/`는 Memgraph write transaction 실행만 담당한다.
- `documents.py`는 최초 원문 저장만 담당한다. 이 단계는 agent가 아니라 ingestion
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
| `register_document` | 사용자가 업로드한 원문을 graph construction 시작 전에 `Document` node로 저장할 때 사용한다. |
| `write_chunks_for_document` | `chunking_agent`가 만든 chunk payload를 저장하고 generated `chunk_ids`를 받아야 할 때 사용한다. |
| `write_relationship_candidates` | `graph_candidate_agent`가 기존 graph와의 proposed edge를 `RelationshipCandidate` node로 저장할 때 사용한다. |
| `write_candidate_revisions` | retry/revision flow에서 기존 candidate의 새 version을 저장할 때 사용한다. |
| `update_candidate_review_status` | review graph가 approve/deny/retry 상태를 candidate에 반영할 때 사용한다. |
| `store_review_note` | 사용자가 candidate review note를 남겼을 때 `ReviewNote` node로 저장할 때 사용한다. |
| `materialize_candidate_edge` | approve된 `RelationshipCandidate`를 실제 graph relationship으로 반영할 때 사용한다. |
| `update_chunk_embeddings` | embedding worker/service가 chunk embedding vector와 status를 업데이트할 때 사용한다. |
| `upsert_ingest_job_progress` | ingestion/pipeline progress를 `IngestJob` operational node로 저장할 때 사용한다. |
