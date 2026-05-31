# External Adapters

`external/`은 RAG backend가 외부 시스템과 통신하기 위한 adapter layer이다.
business logic, agent prompt, pipeline orchestration, API route를 두지 않는다.

## 역할

```text
external/
├── memgraph/     # Memgraph Bolt driver adapter
└── openrouter/   # OpenRouter-compatible LLM / embedding client adapter
```

## `external/memgraph`

Memgraph와 Neo4j-compatible Bolt driver 연결을 관리한다.

- `MemgraphBoltClient`는 Cypher read/write 실행과 결과 serialization만 담당한다.
- `get_memgraph_bolt_client()`가 process-local singleton client를 제공한다.
- query business logic은 `query/read`, `query/write`에 둔다.
- API, MCP, pipeline, tool layer가 driver를 직접 만들지 않는다.

## `external/openrouter`

OpenRouter-compatible LangChain client 생성을 담당한다.

- `create_openrouter_chat_model()`은 graph ingest sub-agent용 chat model을 만든다.
- `create_openrouter_embeddings()`는 chunk embedding용 embedding client를 만든다.
- model name, API key, base URL, embedding dimension은 `settings.py`의 `RAG_`
  환경변수를 따른다.
- agent prompt와 pipeline 실행 순서는 이 layer에 두지 않는다.

## Boundary

- 외부 SDK/client lifecycle은 `external/`에 둔다.
- Memgraph query 함수는 `query/`에 둔다.
- agent tool wrapper는 `tools/`에 둔다.
- LangGraph 실행 흐름은 `pipeline/`에 둔다.
- HTTP/MCP 노출은 `api/`에 둔다.
