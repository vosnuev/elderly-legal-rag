# v3 Service Architecture Diagrams

이 파일은 v3 PPT에서 사용한 diagram-as-code 원본이다. PPT 안에서는 Mermaid 이미지를 그대로 붙이지 않고, 같은 구조를 artifact-tool native shape로 다시 렌더링했다.

## Slide 4. Simplified End-to-End Architecture

```mermaid
flowchart LR
    U[User] --> FE[Streaming Frontend]
    FE -->|chat stream request| BE[Main Backend<br/>LLM Chat Runtime]
    BE -->|LLM call| LLM[LLM Provider]
    BE -->|MCP tool call| MCPClient[MCP Client]
    MCPClient --> MCP[RAG MCP Server<br/>read-only tools]
    MCP --> MG[(Memgraph<br/>Knowledge Graph)]

    RAGFE[RAG Admin FE<br/>Upload / Review / Memory] --> RAGBE[RAG Backend API]
    RAGBE --> Q[Task Queue]
    Q --> W[Graph Build Worker]
    W --> MG
    W --> RC[RelationshipCandidate]
    RC --> REVIEW[Human Review]
    REVIEW --> MG
    RAGBE --> MCP
```

```text
direction right

User [shape: oval, icon: user]
Streaming Frontend [icon: monitor, color: blue]
Main Backend [icon: server, color: purple] {
  Chat Stream API [icon: radio]
  LLM Runtime [icon: brain]
  MCP Client [icon: plug]
}
GraphRAG System [icon: network, color: green] {
  RAG Admin FE [icon: layout-dashboard]
  RAG Backend API [icon: server-cog]
  Task Queue [icon: list]
  Worker [icon: workflow]
  RAG MCP Server [icon: plug-zap]
}
Memgraph [shape: cylinder, icon: database]

User > Streaming Frontend
Streaming Frontend > Chat Stream API
LLM Runtime > MCP Client
MCP Client > RAG MCP Server: read-only tool call
Worker > Memgraph: approved graph write
RAG MCP Server > Memgraph: read
```

## Slide 6. Streaming Frontend Runtime

```mermaid
sequenceDiagram
    participant User
    participant FE as Streaming Frontend
    participant BE as Main Backend

    User->>FE: 질문 입력
    FE->>BE: stream request
    BE-->>FE: message.started
    BE-->>FE: token.delta
    BE-->>FE: tool.started / tool.result
    BE-->>FE: citation.ready
    BE-->>FE: message.completed
    FE-->>User: 실시간 답변 렌더링
```

## Slide 7. Main Backend LLM Chat Runtime

```mermaid
flowchart LR
    FE[Streaming Frontend] --> API[Chat Stream API]
    API --> SESSION[Session / Conversation Context]
    SESSION --> ORCH[LLM Agent Orchestrator]
    ORCH --> PROMPT[Prompt + Policy]
    ORCH --> LLM[LLM Provider]
    ORCH --> TOOLS[Tool Router]
    TOOLS --> MCP[MCP Client]
    MCP --> RAG[RAG MCP Server]
    RAG --> GRAPH[(Memgraph)]
    ORCH --> STREAM[Stream Event Builder]
    STREAM --> FE
```

## Slide 8. Backend to RAG via MCP

```mermaid
flowchart LR
    BE[Main Backend<br/>Answer Runtime] -->|tool call| MCPClient[MCP Client]
    MCPClient -->|schema_read| MCPServer[RAG MCP Server]
    MCPClient -->|text_search| MCPServer
    MCPClient -->|vector_search| MCPServer
    MCPClient -->|graph_traverse| MCPServer
    MCPServer --> MG[(Memgraph)]
    Builder[GraphRAG Builder<br/>Ingest / Review / Memory] -->|write approved graph| MG
    MCPServer -. no write .-> MG
```

## Slide 10. Async Ingest and Construction Graph

```mermaid
flowchart LR
    FE[RAG FE Upload] --> API[Document Upload API]
    API --> DOC[(Document Node)]
    API --> JOB[Create IngestJob]
    JOB --> Q[Task Queue]
    Q --> W[Worker]
    W --> LOAD[document_load]
    LOAD --> CHUNK[chunking_agent]
    CHUNK --> EMBED[embedding_dispatch]
    EMBED --> CAND[graph_candidate_agent]
    CAND --> REVIEW[pending_review]
```

## Slide 12. Review Queue

```mermaid
flowchart LR
    AGENT[LLM Agent] --> CAND[RelationshipCandidate<br/>pending_review]
    CAND --> UI[Review Queue UI]
    UI --> APPROVE[Approve]
    UI --> DENY[Deny]
    APPROVE --> COMMIT[Atomic Review Commit]
    COMMIT --> EDGE[Actual Graph Edge]
    DENY --> REJECT[Rejected Candidate]
    EDGE --> MG[(Memgraph)]
    REJECT --> MG
```

