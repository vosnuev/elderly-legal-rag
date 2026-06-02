# Query Layer Testing

이 문서는 coding agent가 `query/read`와 `query/write` layer를 실제 Memgraph 기준으로
검증하기 위한 절차이다. mock/dry-run이 아니라, 필요한 경우 Docker로 떠 있는 Memgraph에
직접 write/read를 수행한다.

## 전제

- 명령은 `rag/be` 디렉토리에서 실행한다.
- Python 실행은 반드시 `uv run`을 사용한다.
- 로컬 Memgraph는 `rag/infra/docker-compose.yml`로 올라온 container를 사용한다.
- write smoke는 실제 DB에 `manual-smoke-*` 또는 `live-test-*` record를 남긴다.

```bash
cd /home/wonbeenlee/workspace/SKN28-3rd-1Team/rag/be
```

컨테이너 상태 확인:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

기대 상태:

- `rag-memgraph`: healthy, Bolt `127.0.0.1:7687`
- `rag-memgraph-lab`: Lab `127.0.0.1:3000`

## 빠른 검증

unit/integration test:

```bash
PYTHONPATH=src uv run python -m unittest tests.test_query_methods tests.test_endpoint_tools
PYTHONPATH=src uv run python -m unittest discover -s tests
```

live Memgraph write/read test:

```bash
RAG_TEST_MEMGRAPH=1 PYTHONPATH=src uv run python -m unittest tests.test_live_memgraph_query
```

`RAG_TEST_MEMGRAPH=1` test는 실제 DB에 `live-test-*` node와 edge를 생성한다.

## Read-Only Live Smoke

DB 연결, bounded read, autocommit schema read를 확인한다.

```bash
PYTHONPATH=src uv run python - <<'PY'
from external.memgraph import get_memgraph_bolt_client
from query.read.core import read_query, schema_read

get_memgraph_bolt_client().verify_connectivity()
print("connectivity=ok")

print(read_query("MATCH (n) RETURN count(n) AS node_count", max_rows=1))

schema = schema_read()
print({
    "source": schema["source"],
    "node_schema_count": len(schema["nodes"]),
    "edge_schema_count": len(schema["edges"]),
})
PY
```

주의: `schema_read()`는 Memgraph `SHOW SCHEMA INFO`를 사용한다. 이 query는 managed
transaction에서 실패하므로 `external.memgraph.MemgraphBoltClient.execute_autocommit_read`
경로로 실행되어야 한다.

## Query Function Coverage

### Read

| 함수 | 검증 방법 | 기대 결과 |
| --- | --- | --- |
| `read_query` | `MATCH (n) RETURN count(n)` 실행 | read result에 `access=read`, `row_count=1` |
| `schema_read` | 위 read-only smoke 실행 | `source=SHOW SCHEMA INFO`, schema rows 반환 |
| `text_search` | text index가 준비된 DB에서 exact term 검색 | Memgraph `text_search.search` procedure 호출 |
| `vector_search` | vector index와 embedding이 준비된 DB에서 검색 | Memgraph `vector_search.search` procedure 호출 |
| `graph_traverse` | known node id 기준 traversal | bounded path rows 반환 |
| `read_document_by_id` | DB-generated `document_id` 조회 | document properties 반환 |
| `read_node_by_id` | generated `chunk_id`, `candidate_id` 조회 | node properties 반환 |
| `list_chunks_for_document` | smoke document id로 조회 | `HAS_CHUNK`로 연결된 chunk 반환 |
| `list_candidates_for_job` | smoke job id로 조회 | 해당 job의 `RelationshipCandidate` 반환 |
| `list_review_notes_for_candidate` | approved smoke candidate id로 조회 | `HAS_REVIEW_NOTE` note 반환 |
| `list_materialized_edges_for_candidate` | approved smoke candidate id로 조회 | actual edge와 candidate provenance 반환 |
| `read_ingest_job` | smoke job id로 조회 | `IngestJob` progress node 반환 |
| `list_pending_review_candidates` | pending candidate 존재 시 조회 | pending review projection 반환 |

`text_search`, `vector_search`, edge search 계열은 Memgraph index/procedure 준비 상태에
의존한다. index가 없으면 실패를 감추지 말고 Memgraph error를 그대로 확인한다.

### Write

| 함수 | 검증 방법 | 기대 결과 |
| --- | --- | --- |
| `register_document` | `DocumentNode`를 저장 | DB-generated `document_id` 반환, raw content 저장 |
| `write_chunks_for_document` | saved document에 chunk payload 저장 | DB-generated `chunk_ids`, `HAS_CHUNK` edge |
| `write_relationship_candidates` | existing left/right node로 candidate 저장 | generated `edge_candidate_ids`, candidate status `pending_review` |
| `write_candidate_revisions` | previous candidate id와 revised candidate 저장 | `previous_candidate_id`, incremented version 저장 |
| `store_review_note` | candidate에 reviewer note 저장 | `ReviewNote`, `HAS_REVIEW_NOTE` edge |
| `update_candidate_review_status` | candidate status update | enum value만 저장 가능 |
| `materialize_candidate_edge` | approved candidate를 actual edge로 반영 | actual relationship, edge provenance, candidate approved |
| `update_chunk_embedding` | embedded chunk update | `embedding_status`, `embedding_model`, `embedding` 저장 |
| `upsert_ingest_job_progress` | job progress 저장 | `IngestJob` node upsert |

`RelationshipCandidate` write 규칙:

- `left_node`, `right_node`는 필수이고 DB에 실제 존재해야 한다.
- `evidence_node_id`는 optional이다. 다른 문서/청크가 두 endpoint의 관계를 언급했을 때
  provenance anchor로만 사용한다.
- `status`는 `pending_review`, `approved`, `rejected`, `retry` 중 하나만 허용한다.
- `relationship_direction`은 `left_to_right`, `right_to_left`, `bidirectional` 중 하나만
  허용한다.

chunk boundary marker 검증:

- `tools.check_document_unique_string_tool`에 `document_id`와 marker 후보 문자열을 넘긴다.
- `is_unique == true`이면 `start_unique_string` 또는 `end_unique_string`으로 사용할 수
  있다.
- `occurrence_count > 1`이면 agent가 marker 후보를 더 길게 잡아서 다시 검사한다.

## Full Write Smoke With Sample Data

이 script는 `sample_datas/*raw.json` 중 하나를 읽어서 실제 DB에 다음 flow를 생성한다.

```text
Document
  -[:HAS_CHUNK]-> Chunk
Chunk
  -[:EVIDENCES_RELATIONSHIP_CANDIDATE]-> RelationshipCandidate
Chunk
  -[:CANDIDATE_LEFT]-> RelationshipCandidate
RelationshipCandidate
  -[:CANDIDATE_RIGHT]-> Document
RelationshipCandidate
  -[:HAS_REVIEW_NOTE]-> ReviewNote
Chunk
  -[:REFERENCES]-> Document
IngestJob
```

실행:

```bash
PYTHONPATH=src uv run python - <<'PY'
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import json

from pipeline.schemas import GraphIngestPhase
from query.read.inspection import (
    list_candidates_for_job,
    list_chunks_for_document,
    list_materialized_edges_for_candidate,
    list_review_notes_for_candidate,
)
from query.schema import DocumentNode, RelationshipCandidateStatus
from query.write import (
    materialize_candidate_edge,
    register_document,
    store_review_note,
    update_candidate_review_status,
    upsert_ingest_job_progress,
    write_chunks_for_document,
    write_relationship_candidates,
)

sample_path = sorted(Path("../sample_datas").glob("*raw.json"))[0]
raw_content = sample_path.read_text(encoding="utf-8")
json.loads(raw_content)

now = datetime.now(UTC)
suffix = now.strftime("%Y%m%d%H%M%S")
job_id = f"manual-smoke-job-{suffix}"
chunk_text = raw_content[:600]

document = DocumentNode(
    entry_number=int(now.timestamp()),
    document_version=1,
    content_hash=sha256(raw_content.encode("utf-8")).hexdigest(),
    raw_content=raw_content,
    file_name=sample_path.name,
    source_type="json",
    source_path=str(sample_path),
    metadata={
        "registered_at": now.isoformat(),
        "last_ingest_job_id": job_id,
        "smoke_test": True,
    },
)

document_result = register_document(document)
document_id = document_result["rows"][0]["document_id"]

chunk_result = write_chunks_for_document(
    document_id=document_id,
    job_id=job_id,
    chunks=[
        {
            "chunk_index": 1,
            "text": chunk_text,
            "start_unique_string": raw_content[:40],
            "end_unique_string": raw_content[560:600],
            "tags": ["sample-smoke"],
            "summary": "sample smoke chunk",
            "reason": "manual query/write layer smoke test using sample_datas",
            "start_char": 0,
            "end_char": len(chunk_text),
            "metadata": {"smoke_test": True, "sample_file": sample_path.name},
        }
    ],
)
chunk_id = chunk_result["rows"][0]["chunk_ids"][0]

candidate_result = write_relationship_candidates(
    [
        {
            "job_id": job_id,
            "left_node": chunk_id,
            "right_node": document_id,
            "relationship_type": "REFERENCES",
            "relationship_direction": "left_to_right",
            "evidence_node_id": chunk_id,
            "evidence_text": chunk_text[:200],
            "rationale": "manual smoke candidate for query/write verification",
            "status": RelationshipCandidateStatus.PENDING_REVIEW,
            "version": 1,
            "metadata": {"smoke_test": True},
        }
    ]
)
candidate_id = candidate_result["rows"][0]["edge_candidate_ids"][0]

store_review_note(
    candidate_id=candidate_id,
    action="yes",
    reviewer="manual-smoke",
    note="manual smoke approval note for query/write verification",
)

materialize_candidate_edge(candidate_id=candidate_id, reviewer="manual-smoke")
update_candidate_review_status(
    candidate_id=candidate_id,
    status=RelationshipCandidateStatus.APPROVED,
    reviewer="manual-smoke",
)

upsert_ingest_job_progress(
    job_id=job_id,
    phase=GraphIngestPhase.COMPLETED.value,
    document_id=document_id,
    chunk_count=1,
    candidate_count=1,
    pending_review_count=0,
    warnings=[],
    errors=[],
)

chunks = list_chunks_for_document(document_id, limit=10)
candidates = list_candidates_for_job(job_id, limit=10)
notes = list_review_notes_for_candidate(candidate_id, limit=10)
edges = list_materialized_edges_for_candidate(candidate_id, limit=10)

print({
    "job_id": job_id,
    "document_id": document_id,
    "chunk_id": chunk_id,
    "candidate_id": candidate_id,
    "chunk_rows": chunks["row_count"],
    "candidate_rows": candidates["row_count"],
    "note_rows": notes["row_count"],
    "edge_rows": edges["row_count"],
})
PY
```

성공 기준:

- `chunk_rows == 1`
- `candidate_rows == 1`
- `note_rows == 1`
- `edge_rows == 1`

## Optional Evidence Smoke

`evidence_node_id` 없이 endpoint만으로 candidate를 저장할 수 있어야 한다. 이 경우
`EVIDENCES_RELATIONSHIP_CANDIDATE` edge는 생성되지 않고, `CANDIDATE_LEFT`,
`CANDIDATE_RIGHT`만 생성된다.

```bash
PYTHONPATH=src uv run python - <<'PY'
from uuid import uuid4

from query.write import register_document, write_relationship_candidates
from query.schema import DocumentNode

left_id = f"optional-evidence-left-{uuid4().hex[:8]}"
right_id = f"optional-evidence-right-{uuid4().hex[:8]}"

for node_id, name in ((left_id, "left"), (right_id, "right")):
    register_document(
        DocumentNode(
            id=node_id,
            entry_number=0,
            document_version=1,
            content_hash=node_id,
            raw_content=f"{name} endpoint document",
            file_name=f"{name}.txt",
            source_type="txt",
            metadata={"smoke_test": True},
        )
    )

result = write_relationship_candidates(
    [
        {
            "job_id": "optional-evidence-smoke",
            "left_node": left_id,
            "right_node": right_id,
            "relationship_type": "RELATED_TO",
            "relationship_direction": "left_to_right",
            "evidence_text": "direct endpoint relationship without separate evidence node",
            "rationale": "optional evidence smoke",
        }
    ]
)
print(result["rows"][0])
PY
```

성공 기준:

- `stored_count == 1`
- `linked_left_count == 1`
- `linked_right_count == 1`
- `linked_evidence_count == 0`

## Memgraph Lab 확인 Query

전체 graph 확인:

```cypher
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 300;
```

manual smoke만 확인:

```cypher
MATCH (n)
WHERE n.id STARTS WITH "manual-smoke"
   OR n.job_id STARTS WITH "manual-smoke"
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;
```

candidate review artifact 확인:

```cypher
MATCH (left)-[:CANDIDATE_LEFT]->(candidate:RelationshipCandidate)-[:CANDIDATE_RIGHT]->(right)
OPTIONAL MATCH (evidence)-[:EVIDENCES_RELATIONSHIP_CANDIDATE]->(candidate)
OPTIONAL MATCH (candidate)-[:HAS_REVIEW_NOTE]->(note:ReviewNote)
RETURN left, candidate, right, evidence, note
LIMIT 100;
```

approved actual edge 확인:

```cypher
MATCH (left)-[edge]->(right)
WHERE edge.candidate_id IS NOT NULL
RETURN left, edge, right
LIMIT 100;
```

## 실패 해석

- `SHOW SCHEMA INFO query is not allowed in multicommand transactions`
  - `schema_read()`가 autocommit path를 타지 않는 것이다.
- `RelationshipCandidate write stored 0 rows`
  - `left_node` 또는 `right_node` id가 DB에 존재하지 않는다.
- `RelationshipCandidateStatus` validation error
  - status가 `pending_review`, `approved`, `rejected`, `retry` 중 하나가 아니다.
- `Unsafe Cypher identifier`
  - materialized edge의 `relationship_type`이 Cypher identifier로 안전하지 않다.
- Memgraph procedure/index error
  - text/vector index 또는 procedure 준비 상태 문제이다. query layer에서 fallback하지 않는다.
