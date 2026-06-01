# Tools Layer

`tools/`는 LangChain agent에게 제공되는 tool wrapper와 tool argument schema를
담당한다. 여기의 tool은 `query/`의 database query function을 감싸서 agent가
사용할 수 있는 interface로 만든다.

## 책임 한도

- LangChain `@tool` wrapper 정의.
- agent가 보는 tool argument schema 정의.
- query layer function을 agent-friendly input/output으로 감싼다.
- 내부 graph construction agent에게 read/write tool을 제공한다.

## 하지 않는 것

- Memgraph driver를 직접 만들지 않는다.
- database storage schema의 원본 정의를 소유하지 않는다.
- FastAPI endpoint나 MCP server를 만들지 않는다.
- LangGraph state를 저장하지 않는다.
- worker job status를 관리하지 않는다.
- hidden `ContextVar`로 `job_id`, `document_id`, `chunk_id`를 주입하지 않는다.

## Tool Schema 원칙

tool schema는 agent input contract이다. 따라서 agent가 의미적으로 결정해야 하는
값만 받는다.

- agent가 생성할 수 있는 값: chunk text, source boundary marker, relationship type,
  left/right node reference, relationship direction, evidence node reference,
  evidence, rationale, reviewer note.
- agent가 생성하면 안 되는 값: database-generated id, worker job id, candidate status,
  candidate version, hidden runtime context field.

저장 성공 후 생성된 `chunk_ids`, `edge_candidate_ids` 같은 technical identifier는
tool 결과로 반환한다.

## 디렉토리 구조

```text
tools/
├── __init__.py              # agent가 import할 tool export
├── memgraph_read_tools.py   # query/read를 감싼 read-only agent tools
├── chunk_tools.py           # chunk 생성 관련 agent write tools
├── candidate_tools.py       # edge candidate 생성/revision 관련 agent write tools
├── review_context_tools.py  # reviewer note 조회용 tools
└── README.md
```

## 파일 역할

### `memgraph_read_tools.py`

내부 agent가 Memgraph를 읽기 위한 tool wrapper이다.

- schema read
- raw read query
- text search
- vector search
- graph traversal
- existing context probe

동일한 query/read function은 외부 MCP read tool에서도 재사용할 수 있다.

### `chunk_tools.py`

`chunking_agent`가 원문 document를 읽고 `Chunk`를 저장하기 위해 사용하는 tool을 둔다.

이 파일 안의 Pydantic schema는 agent input schema이다. 향후 DB schema가
`query/schema/`의 `ChunkNode` storage contract를 기준으로 하는 agent-write subset이다.
chunk id는 agent 입력으로 받지 않고 `query/write/chunks.py`가 저장 시 생성한 뒤 결과로
반환한다.

Boundary marker 검증은 `check_document_unique_string_tool`을 사용한다. agent는
`document_id`와 marker 후보 문자열을 넘기고, tool 결과의 `is_unique`,
`occurrence_count`, 첫 위치 정보를 보고 marker 길이를 늘리거나 확정한다.

### `candidate_tools.py`

`graph_candidate_agent`와 candidate revision agent가 edge candidate를 저장하기 위해
사용하는 tool을 둔다.

여기서 candidate는 chunk candidate가 아니라 relationship edge candidate이다.
edge candidate의 두 endpoint는 `left_node`와 `right_node`로 표현하고, 실제 승인 edge의
방향은 `relationship_direction`으로 표현한다. candidate를 뒷받침하는 근거 node는
chunk 전용 필드가 아니라 `evidence_node_id`로 받는다.
candidate id는 agent 입력으로 받지 않고 저장 시 생성한 뒤 결과로 반환해야 한다.
candidate status와 version도 agent 입력으로 받지 않고 query/write layer가 기본값과
retry version을 결정한다.
실제 persistence Cypher는 `query/write/candidates.py`가 담당한다.

### `review_context_tools.py`

reviewer note 조회 tool을 둔다. ingest state 조회는 별도 전용 tool을 만들지 않고
agent가 일반 Memgraph read tool을 통해 필요한 범위만 읽는다.

## 전체 플로우에서 위치

```text
pipeline/sub_agents
  -> tools
      -> query/read, query/write
          -> external/memgraph
```

외부 MCP는 `tools/`를 그대로 노출하는 구조가 아니다. MCP는 read-only query function을
별도 server interface로 감싼다.
