# Slide 08. Document Construction Graph

## 사용 위치

- PPT slide 8
- 발표 구간: 첫 번째 graph pipeline

## 슬라이드에서 말할 내용

LangGraph 기반 construction graph는 document load, chunking, embedding dispatch, graph candidate generation 순서로 실행된다. 마지막 agent는 실제 edge가 아니라 review 대상 candidate를 만든다.

## 원본 근거

- `rag/be/src/pipeline/graphs/document_construction_graph.py`
- `rag/be/src/pipeline/sub_agents/chunking_agent.py`
- `rag/be/src/pipeline/node_services/document_construction/embedding_dispatch_node_service.py`
- `rag/be/src/pipeline/sub_agents/graph_candidate_agent.py`
- `rag/be/src/query/write/chunks.py`
- `rag/be/src/query/write/embeddings.py`
- `rag/be/src/query/write/candidates.py`

## Mermaid

```mermaid
flowchart TD
    Start["START\njob_id + document_id"] --> Load["document_load_node_service\nvalidate Document exists"]
    Load --> Chunk["chunking_agent\nread document by id\nwrite Chunk nodes"]
    Chunk --> ChunkIds["chunk_ids\nDB-generated UUID"]
    ChunkIds --> Embed["embedding_dispatch_node_service\nfor each chunk: read -> embed -> update"]
    Embed --> Candidate["graph_candidate_agent\nchunk-level agent runs"]

    Candidate --> ReadTools["Memgraph read tools\nschema / read / text / vector / traverse"]
    Candidate --> ChunkTool["read_chunk_context_tool\ncurrent evidence chunk"]
    Candidate --> WebSearch["Firecrawl search\noptional external evidence"]
    Candidate --> Memory["Injected Memory Context\nuser preference layer"]

    Candidate --> WriteCandidate["write_relationship_candidate_tool"]
    WriteCandidate --> CandidateNode[("RelationshipCandidate\nstatus=pending_review")]
    CandidateNode --> End["END\nphase=PENDING_REVIEW"]
```

## PPT 구성 제안

- main path는 굵은 선으로, tool/context는 얇은 보조 선으로 표시한다.
- `RelationshipCandidate`를 실제 edge와 다른 색으로 표시한다.

