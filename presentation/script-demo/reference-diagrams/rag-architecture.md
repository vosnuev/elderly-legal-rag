# RAG Architecture Reference Diagrams

이 파일은 발표 자료 제작용 Mermaid reference이다. 슬라이드에는 필요한 다이어그램만 복사해서 사용한다.

## 1. 전체 프로젝트/컨테이너 아키텍처

```mermaid
flowchart TB
    subgraph UserLayer["User / Demo Surface"]
        Streamlit["streamlit/\n서비스 사용자 화면\n상담/질문 UI"]
        RagOpsFE["rag/fe\nRAG 운영/데모 UI\nDocuments, Graph Jobs, Review Queue, Memory"]
        CodexClient["External MCP Client\nCodex / Agent Runtime"]
    end

    subgraph AppServices["Application Services"]
        MainBackend["backend/\n메인 상담 agent backend\nLangGraph/LangChain runtime"]
        RagBackend["rag/be\nRAG backend\nFastAPI + FastMCP + Worker Runtime"]
    end

    subgraph RuntimeInfra["Runtime Infra"]
        Memgraph[("Memgraph Docker\nDocument / Chunk / Candidate / ReviewNote / Memory / Edges")]
        Redis[("Redis Docker\nObservability Streams\nWorker Events / Agent Events")]
        OpenRouter["OpenRouter / LLM Providers\nDeepSeek, GPT OSS, Qwen, etc."]
        Firecrawl["Firecrawl Search API\nExternal evidence search"]
    end

    Streamlit --> MainBackend
    MainBackend -. "read-only MCP tools" .-> RagBackend
    CodexClient -. "read-only MCP tools" .-> RagBackend
    RagOpsFE --> RagBackend

    RagBackend --> Memgraph
    RagBackend --> Redis
    RagBackend --> OpenRouter
    RagBackend --> Firecrawl

    MainBackend --> OpenRouter
```

### 설명

- `streamlit/`: 최종 사용자 상담/질문 UI 성격의 화면.
- `backend/`: 실제 상담 agent runtime. 이후 RAG MCP server를 소비하는 쪽이다.
- `rag/fe`: RAG 구축/검수/운영을 위한 데모 UI.
- `rag/be`: RAG backend. 프론트엔드 API, 비동기 worker pipeline, read-only MCP server를 함께 제공한다.
- `Memgraph`: graph RAG storage.
- `Redis`: job/agent observability stream.

## 2. RAG backend 내부 역할 3분할

```mermaid
flowchart LR
    subgraph FrontendApiBoundary["FE API Boundary"]
        UploadApi["Document Upload API"]
        JobsApi["Graph Jobs API"]
        ReviewApi["Review Queue API"]
        MemoryApi["Memory Settings API"]
        EventApi["SSE / Polling Events API"]
    end

    subgraph ProcessingBoundary["Processing Boundary"]
        TaskSubmitter["Task Submitter"]
        WorkerPool["Worker Pool\nbuild lane / review lane"]
        Runner["Worker Runner"]
        ConstructionGraph["Document Construction Graph"]
        ReviewGraph["Candidate Review Graph"]
    end

    subgraph McpBoundary["External MCP Boundary"]
        FastMCP["FastMCP Streamable HTTP"]
        ReadTools["Read-only Tools\nschema/read query/text/vector/traverse"]
    end

    subgraph StorageBoundary["Storage / Providers"]
        Memgraph[("Memgraph")]
        Redis[("Redis Streams")]
        LLM["LLM Providers"]
        WebSearch["Firecrawl"]
    end

    UploadApi --> TaskSubmitter
    ReviewApi --> TaskSubmitter
    JobsApi --> Memgraph
    MemoryApi --> Memgraph
    EventApi --> Redis

    TaskSubmitter --> WorkerPool
    WorkerPool --> Runner
    Runner --> ConstructionGraph
    Runner --> ReviewGraph

    ConstructionGraph --> Memgraph
    ConstructionGraph --> LLM
    ConstructionGraph --> WebSearch
    ReviewGraph --> Memgraph
    ReviewGraph --> LLM
    Runner --> Redis

    FastMCP --> ReadTools
    ReadTools --> Memgraph
```

### 설명

`rag/be`는 하나의 서버지만 역할은 세 가지로 나뉜다.

1. FE API boundary: 문서 업로드, job 상태, review queue, memory 설정.
2. Processing boundary: task queue와 worker pool이 graph pipeline을 실행.
3. MCP boundary: 외부 agent가 graph를 읽을 수 있는 read-only tool surface.

## 3. Document Construction Graph

```mermaid
flowchart TD
    FE["User uploads document"] --> Api["POST /api/ingest/..."]
    Api --> RegisterDoc["Register Document\nMemgraph randomUUID() document_id"]
    RegisterDoc --> CreateJob["Create IngestJob\njob_id"]
    CreateJob --> QueueBuild["Queue build task"]
    QueueBuild --> Worker["Build worker"]

    Worker --> LoadDoc["document_load_service\nload by document_id"]
    LoadDoc --> ChunkAgent["chunking_agent\nread document, write chunks"]
    ChunkAgent --> ChunkNodes[("Chunk nodes\nDB-generated chunk_id")]
    ChunkNodes --> Embedding["embedding dispatch service\nfor each chunk: read -> embed -> update"]
    Embedding --> CandidateAgent["graph_candidate_agent\nper chunk concurrent workers"]

    CandidateAgent --> ReadMemgraph["Memgraph read tools\nschema/read/text/vector/traverse"]
    CandidateAgent --> SearchWeb["Firecrawl web search\noptional public evidence"]
    CandidateAgent --> MemoryContext["Agent Memory Context\nautomatically injected"]
    CandidateAgent --> CandidateWrite["write_relationship_candidate_tool"]
    CandidateWrite --> RelationshipCandidate[("RelationshipCandidate\nstatus=pending_review")]
    RelationshipCandidate --> PendingReview["Job phase: PENDING_REVIEW"]
```

### 설명

- document와 chunk id는 DB-generated id를 사용한다.
- chunking agent는 raw document를 state에 싣지 않고 document id 기반으로 DB에서 읽는다.
- embedding은 새 노드를 만들지 않고 기존 Chunk node에 vector property를 업데이트한다.
- graph candidate agent는 실제 edge를 쓰지 않고 RelationshipCandidate만 쓴다.

## 4. Candidate Review Graph와 Memory Feedback Loop

```mermaid
flowchart TD
    ReviewQueue["FE Review Queue"] --> Draft["Local approve/deny draft"]
    Draft --> Commit["Atomic Commit\nbatch review task"]
    Commit --> ReviewWorker["Review worker lane\nsingle worker default"]

    ReviewWorker --> ApplyDecision["Apply candidate decisions"]
    ApplyDecision --> Approved{"Approved?"}
    Approved -->|yes| Materialize["Materialize actual graph edge"]
    Approved -->|no| Rejected["Set candidate.status = rejected"]

    ApplyDecision --> StoreNote{"Reviewer note exists?"}
    StoreNote -->|yes| ReviewNote[("ReviewNote")]
    StoreNote -->|no| SkipNote["No ReviewNote\nmemory update can be skipped if no notes"]

    RelationshipCandidate[("RelationshipCandidate")] -->|HAS_REVIEW_NOTE| ReviewNote
    ReviewNote -->|EVIDENCES_MEMORY| Memory[("Memory\nsingle curated markdown document")]
    ReviewWorker --> MemoryUpdate["memory_update_agent\nrewrite Memory from current memory + review_context"]
    MemoryUpdate --> Memory

    Memory --> NextCandidateAgent["Next graph_candidate_agent run\nMemory injected into context"]
```

### 설명

- ReviewNote는 candidate review feedback event이다.
- Memory는 ReviewNote를 그대로 누적하는 append log가 아니라 curated markdown 문서이다.
- 다음 candidate generation 때 Memory가 자동 주입된다.
- 발표 표현: "사용자와 함께 작업할수록 agent의 판단 기준이 누적된다."

## 5. Memgraph 저장 모델

```mermaid
flowchart LR
    Document[("Document\nraw source document")] -->|HAS_CHUNK| Chunk[("Chunk\ntext + embedding")]

    Chunk -->|CANDIDATE_LEFT| Candidate[("RelationshipCandidate\nproposed edge")]
    Candidate -->|CANDIDATE_RIGHT| Chunk2[("Chunk")]
    Chunk -. "EVIDENCES_RELATIONSHIP_CANDIDATE" .-> Candidate

    Candidate -->|HAS_REVIEW_NOTE| ReviewNote[("ReviewNote\nreviewer feedback")]
    ReviewNote -->|EVIDENCES_MEMORY| Memory[("Memory\nagent preference layer")]

    Candidate -->|approved materialization| ActualEdge["Actual graph relationship\nRELATED_TO / DEFINES_TERM_FOR / etc."]
```

### 설명

- `RelationshipCandidate`는 semantic edge가 아니라 workflow artifact이다.
- approved candidate만 실제 graph relationship으로 materialize된다.
- Memory의 durable provenance는 ReviewNote edge와 evidence id arrays로 남는다.

## 6. Observability / Transparency

<!-- 발표 전체 아키텍처 다이어그램에서만 보여줄 것. 세부 이벤트 타입은 발표 본문에서 깊게 다루지 않는다. -->

```mermaid
flowchart LR
    Worker["Worker Runner"] --> Observer["Observability Service"]
    AgentRuntime["LangChain/LangGraph Agent Runtime"] --> EventLogger["AgentEventStreamLogger"]
    EventLogger --> Observer
    Observer --> Redis[("Redis Streams\nrag:observability:jobs:*")]

    Redis --> Sse["SSE Endpoint"]
    Redis --> Polling["Status Polling / Event Fetch"]
    Sse --> RagFE["Graph Jobs / Diagnostics Studio"]
    Polling --> RagFE

    AgentRuntime -. "future telemetry" .-> OpenLIT["OpenLIT"]
    OpenLIT -. "export spans" .-> LangSmith["LangSmith"]
```

### 설명

- Redis Streams는 운영/디버깅용 event stream이다.
- Graph Jobs와 Diagnostics Studio는 worker lifecycle, node service start/end, agent token/event, tool call/result, error를 보여준다.
- LangSmith/OpenLIT는 다음 단계에서 span-level telemetry를 붙일 위치이다.

## 7. 발표용 한 줄 요약

```text
문서 업로드 -> 비동기 construction graph -> RelationshipCandidate 생성 -> 사용자 review -> 실제 edge 확정 -> ReviewNote 기반 Memory update -> 다음 agent run에 Memory 자동 주입 -> read-only MCP로 외부 agent가 graph 사용
```

