# Memgraph MCP GraphRAG PRD

## 1. Executive Summary

### Problem Statement

The project needs a RAG subsystem that continuously grows as public text
documents are added. The previous Microsoft GraphRAG-centered plan is no longer
the primary implementation path. Memgraph is the graph/vector persistence layer,
but Memgraph does not automatically construct the knowledge graph from raw
documents; the project must own parsing, chunking, embedding, relationship
candidate generation, review, and storage.

Legal/welfare documents require hierarchy-aware graph placement. Laws,
ordinances, enforcement rules, regional scope, effective dates, eligibility
conditions, agencies, and source evidence must be connected explicitly.

### Proposed Solution

Build `rag/` as an independent Python RAG backend monolith plus an independent
operations UI:

- `rag/be`: FastAPI service for ingest/status/review APIs, LangGraph agentic
  ingest, Memgraph query/persistence, and FastMCP Streamable HTTP read-only
  server.
- `rag/fe`: Bun/Vite React operations UI for document upload, ingest status, and
  candidate review.
- `rag/infra`: Docker Compose for Memgraph and Memgraph Lab.

The main `backend/` agent does not know RAG implementation details. It calls the
RAG service only through the external read-only MCP endpoint using a LangChain
MCP adapter. Internal ingest agents use in-process LangChain tools and do not go
through external MCP.

### Success Criteria

- Adding a text document grows Memgraph with documents, chunks, embeddings,
  reviewable relationship candidates, approved semantic edges, and provenance.
- The RAG backend stores exact raw text and can trace every chunk/candidate/edge
  back to the source document version.
- Internal ingest agents can probe Memgraph and write generated chunks/candidates
  through context-bound write tools.
- External MCP exposes read-only graph query tools only.
- Query methods use official Memgraph Cypher, text search, vector search, and
  traversal capabilities for the installed Memgraph version.
- The backend main agent can query RAG through MCP without coupling to Memgraph
  code.

## 2. User Experience & Functionality

### User Personas

- End users: ask disability/welfare/legal-support questions and expect grounded
  answers with source evidence.
- HR/employer users: search employment obligation, subsidy, and reasonable
  accommodation rules.
- Welfare/legal support staff: need fast lookup across laws, ordinances, regional
  rules, benefits, agencies, and eligibility conditions.
- RAG operator: uploads public text documents and reviews graph relationship
  candidates.
- Backend agent developer: integrates read-only RAG query tools through MCP.

### User Stories

#### Story 1: Continuously Growing Document Ingest

As a RAG operator, I want to add public text documents so that the knowledge
graph grows without rebuilding from scratch.

Acceptance Criteria:

- Input is text-only for MVP: plain text, JSON, or other text payloads.
- PDF/OCR/VLM handling is out of scope until a later pre-text layer is added.
- Each ingest job tracks source metadata, status, chunks, candidate count, and
  review state.
- Duplicate or changed documents are detected with stable source identifiers and
  content hashes.
- New documents can connect to existing graph records.

#### Story 2: Hierarchy-Aware Graph Construction

As a RAG operator, I want the graph construction agent to understand legal
hierarchy so that laws, ordinances, enforcement rules, and regional scope are
connected correctly.

Acceptance Criteria:

- Prompts explicitly describe the hierarchy `Law -> Ordinance -> EnforcementRule`
  and regional applicability.
- The system can extract or connect domain concepts such as article, policy,
  benefit, eligibility condition, agency, effective date, and region.
- Every semantic relationship candidate includes relationship type, evidence,
  source chunk, and rationale.
- Semantic candidates are pending review until a reviewer approves them.

#### Story 3: Human Review of Relationship Candidates

As a reviewer, I want to approve, reject, or retry candidate relationships so
that only confirmed relationships become graph facts.

Acceptance Criteria:

- LLM-proposed semantic relationships are stored as pending review candidates.
- Yes materializes an actual semantic edge.
- No preserves rejected candidate metadata.
- Retry invokes candidate revision with reviewer note and source context.
- Reviewer notes are persisted for future prompt context.

#### Story 4: External Read-Only MCP Query

As a backend agent developer, I want the main backend agent to query RAG through
a read-only MCP server so that graph construction remains isolated from
user-facing answer generation.

Acceptance Criteria:

- RAG exposes FastMCP over Streamable HTTP.
- External MCP registers no write tools.
- The backend main agent can call read query, text search, vector search, graph
  traversal, and schema-read tools.
- The MCP server returns query results and metadata; final natural-language
  answer generation remains in `backend/`.

#### Story 5: Internal Agentic Graph Placement

As a graph construction agent, I want internal read/write tools so that I can
probe existing graph state and place new document chunks into the graph.

Acceptance Criteria:

- Internal tools are Python/LangChain tools, not external MCP tools.
- Internal LLM agents can use read query, text search, vector search, traversal,
  schema read, and context probe tools.
- `chunking_agent` writes generated chunks through `write_chunk_tool`.
- `graph_candidate_agent` writes relationship candidates through
  `write_relationship_candidate_tool`.
- `graph_candidate_revision_agent` writes retry versions through
  `write_candidate_revision_tool`.
- Internal write tools are context-bound and never ask the LLM for `job_id`,
  task id, `dry_run`, mock, preview, or no-op flags.

#### Story 6: Operations UI Roadmap

As a RAG operator, I want a separate operations UI so that I can upload
documents, start graph add tasks, inspect status, and review candidates.

Acceptance Criteria:

- `rag/fe` is independent from root `frontend/`.
- MVP UI supports document drag/drop or text upload, ingest job status, graph add
  trigger, and pending review summary.
- Graph/document management and visualization are roadmap items, not the first
  implementation target.

### Non-Goals

- RAG MCP server does not generate final user-facing answers.
- External MCP does not expose writes.
- MVP does not ingest PDFs directly.
- MVP does not auto-approve semantic edges by confidence.
- MVP does not implement a legal-advice decision system.
- Microsoft GraphRAG can be used as an ingestion-design reference, but it is not
  the primary runtime dependency.

## 3. AI System Requirements

### LLM and Embedding Providers

- Use OpenRouter as the default LLM gateway.
- Use LangChain-compatible OpenAI-style clients where possible.
- Default embedding model: `openai/text-embedding-3-large`.
- Default embedding dimension: 3072. Memgraph vector index dimensions must match.
- Do not log API keys, secrets, full prompts containing secrets, or credentials.

### MCP Runtime

- Use FastMCP from the official Python MCP SDK.
- Transport: Streamable HTTP.
- External endpoint path: `/mcp`.
- FastMCP exposure belongs under `rag/be/src/api/mcp.py`.
- Internal ingest tools are not registered in MCP.

### External MCP Interface

Purpose:

- Read-only query interface for `backend/` main agent and external consumers.
- The LLM may write read-only Cypher directly or call wrappers.
- Tool server validates read-only behavior, timeouts, row limits, and operation
  allowlists before executing against Memgraph.

Allowed tool surface:

- `memgraph.read_query`: validated bounded read-only Cypher.
- `memgraph.schema_read`: labels, relationship types, key properties, indexes,
  vector index names, and instructions.
- `memgraph.text_search`: Memgraph official text-search wrapper.
- `memgraph.vector_search`: Memgraph vector-search wrapper.
- `memgraph.graph_traverse`: bounded graph neighborhood/path traversal.

Denied operations:

- `CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DROP`, index mutation, and
  arbitrary file/network procedures.

### Internal Ingest Interface

Purpose:

- In-process interface used by graph construction agents.
- Agents receive explicit read and purpose-specific write tools.
- Internal write tools are not exposed through MCP.

Primary code locations:

```text
rag/be/src/tools/
rag/be/src/agents/graph_ingest/sub_agents/
rag/be/src/ingest_tasks/
```

Agent-facing tools:

- Read/query group:
  - `memgraph.schema_read`
  - `memgraph.read_query`
  - `memgraph.text_search`
  - `memgraph.vector_search`
  - `memgraph.graph_traverse`
  - `memgraph.probe_existing_context`
- Chunk write group:
  - `write_chunk_tool`
- Candidate write group:
  - `write_relationship_candidate_tool`
  - `write_candidate_revision_tool`
- Review/context group:
  - `get_reviewer_notes_tool`
  - `get_ingest_state_tool`

Rules:

- Write tools are purpose-specific and context-bound.
- Query-service write methods may exist under the tool implementation, but
  LangChain tool schemas must not expose runtime context or policy flags.
- Raw generic write query is not a default agent tool. If needed later, it must
  be an internal-only context-bound escape hatch.

### Query Service Method Contract

Query/search business logic lives under `rag/be/src/query/`. It is not the same
as LangChain tool exposure. `tools/` wraps query methods into agent-facing tools.

Core query methods:

- `read_query`: bounded read-only Cypher.
- `write_query`: internal-only validated write Cypher called from trusted
  context-bound wrappers.
- `schema_read`: schema, labels, relationship types, indexes, and instructions.
- `text_search`: Memgraph official text-search procedures.
- `vector_search`: Memgraph vector-search procedures.
- `graph_traverse`: bounded path/neighborhood queries.
- `probe_existing_context`: lightweight helper combining primitive reads without
  removing agent search freedom.

Policy:

- Do not add a single combined "hybrid search" tool upfront.
- Keep primitive query methods independently available.
- Any future combined helper must be justified by repeated implementation
  duplication and remain decomposable.
- Traditional keyword/vector score-fusion hybrid RAG is not the current graph
  ingest requirement.

### Raw Cypher Instruction Contract

Tool instructions must include:

- Current graph schema and relationship vocabulary.
- Examples of valid read queries.
- Examples of valid internal write/upsert patterns for context-bound wrappers.
- Vector index names and embedding dimensions.
- Legal hierarchy convention: `Law -> Ordinance -> EnforcementRule`, plus
  regional scope.
- Query safety rules, row limits, timeouts, and forbidden operations.
- Guidance to prefer wrappers when they express the task.
- Guidance to use raw Cypher when wrappers cannot express required graph
  reasoning.

### Prompt Requirements

Graph extraction prompt must include:

- Do not create entities or edges without source chunk evidence.
- Use only schema-approved relationship types.
- Treat `Law -> Ordinance -> EnforcementRule` as the default hierarchy direction.
- Connect regional enforcement rules to region metadata.
- Extract domain properties or candidate entities for target group, application
  requirement, agency, amount/rate, effective date, and article references.
- Store semantic relationships as candidates, not approved graph facts.
- Include source chunk id, evidence span/text, and rationale for every candidate.

Memgraph query-generation prompt must include:

- This is agentic GraphRAG, not a fixed vanilla RAG endpoint.
- Convert user questions or ingest tasks into Cypher or wrapper calls using
  graph schema and tool instructions.
- External MCP must generate read-only queries only.
- Internal write behavior is allowed only through context-bound internal tools.
- Do not invent labels, relationships, or indexes that schema read did not show.
- Keep raw Cypher bounded by row limit, traversal depth, and timeout.

### Evaluation Strategy

- Retrieval Precision@5 for representative user questions.
- Citation/source accuracy against source documents and articles.
- Ingest regression fixtures for legal hierarchy and regional scope.
- Candidate review quality sampled by approved/rejected/retry decisions.
- MCP contract tests proving external read-only exposure.
- Tool schema tests proving internal tools do not expose `job_id` or `dry_run`.

## 4. Technical Specifications

### Architecture Overview

```text
Public text documents
  -> rag/be FastAPI ingest API
  -> document registration
  -> LangGraph agentic ingest
       -> chunking_agent + write_chunk_tool
       -> embedding dispatcher
       -> graph_candidate_agent + write_relationship_candidate_tool
       -> feedback_judge_agent
       -> pending review
  -> Memgraph
       -> raw documents
       -> chunks and embeddings
       -> candidates and reviewer notes
       -> approved semantic edges
       -> ingest jobs
  -> FastMCP read-only endpoint (/mcp)
  -> backend LangChain MCP adapter
  -> backend main agent
```

### Runtime Structure

- `rag/be/src/app.py`: FastAPI bootstrap, router wiring, and MCP app mounting.
- `rag/be/src/api/`: HTTP API routers and external MCP exposure.
- `rag/be/src/ingest_tasks/`: task submission, document registration, status,
  and progress management.
- `rag/be/src/agents/graph_ingest/`: LangGraph orchestration and subagents.
- `rag/be/src/tools/`: singleton LangChain tools and runtime context binding.
- `rag/be/src/query/`: Memgraph query methods and domain repositories.
- `rag/be/src/external/memgraph/`: pure Memgraph Bolt driver adapter.
- `rag/fe`: independent operations UI.
- `rag/infra`: Memgraph and Memgraph Lab Compose files.

### Service Boundary

#### `rag/be`

Responsibilities:

- Document ingest API.
- Ingest job and status management.
- LLM-based chunking and graph candidate generation.
- Embedding dispatch.
- Review workflow APIs.
- Memgraph query/persistence through `query/` and `external/memgraph/`.
- External read-only FastMCP server.

#### `rag/fe`

Responsibilities:

- Document upload workflow.
- Graph add trigger.
- Ingest status display.
- Pending review list and candidate decision UI.

Non-responsibilities:

- Final user chat UI.
- Direct Memgraph connection.
- Direct graph mutation outside backend APIs.

#### `backend/`

Responsibilities:

- User-facing chat API.
- Main LangChain agent orchestration.
- Loading RAG external MCP tools.
- Final answer generation with citations.

Non-responsibilities:

- Direct Memgraph query logic.
- Document parsing.
- Graph construction.
- Embedding storage.

### Graph Storage Requirements

This PRD does not fix the final Memgraph schema. It requires only these storage
capabilities:

- Store raw documents and versions.
- Store chunks linked to source documents.
- Store chunk embeddings compatible with Memgraph vector search.
- Store relationship candidates separately from approved semantic edges.
- Store reviewer notes linked to candidate/document context.
- Store approved edges with provenance to source candidate and evidence.
- Represent legal hierarchy and regional scope.

### Ingest Pipeline

1. Validate text input and metadata.
2. Normalize text as UTF-8.
3. Create/update `Document` and ingest job.
4. `chunking_agent` creates chunks and verifies markers.
5. `chunking_agent` writes chunks through `write_chunk_tool`.
6. `embedding_dispatch_service` creates chunk embeddings.
7. `graph_candidate_agent` probes existing graph context.
8. `graph_candidate_agent` writes relationship candidates through
   `write_relationship_candidate_tool`.
9. `feedback_judge_agent` checks coverage and completion.
10. Job enters `pending_review`.
11. Review action later materializes, rejects, or retries candidates.

### Agentic Query Pipelines

#### External Read-Only Query Pipeline

1. Backend main agent receives a user question.
2. Backend main agent loads external MCP tool instructions and schema.
3. LLM selects read query, text search, vector search, graph traversal, schema
   read, or a combination.
4. MCP validates read-only/bounded behavior.
5. MCP executes against Memgraph.
6. Backend main agent uses results and citations to generate the final answer.

#### Internal Ingest/Graph Placement Pipeline

1. Ingest API stores raw document and creates job.
2. Start API invokes graph add task with `job_id` and `document_id`.
3. Orchestrator builds `AgentToolContext`.
4. Agents receive singleton tools with bound runtime context.
5. Agents query existing graph, write chunks, and write candidates.
6. Services persist deterministic progress, embeddings, review status, notes, and
   actual edge materialization.
7. Job summary records nodes/edges/candidates/status and audit metadata.

### Memgraph Query Requirements

- Use official Memgraph syntax for Cypher, text search, vector search, and
  traversal.
- Vector index dimension must match embedding dimension.
- Traversal must be bounded by depth and row count.
- External query validation rejects writes before DB execution.
- Internal write methods receive trusted bound context and emit audit logs.
- Write operations should be idempotent where possible.
- Candidate storage preserves source chunk and evidence provenance.

### API Surface

HTTP APIs in `rag/be`:

- `GET /health`
- `GET /api/system/dependencies`
- `POST /ingest`
- `GET /ingest/status/{job_id}`
- `POST /api/ingest/jobs`
- `GET /api/ingest/jobs/{job_id}`
- `POST /api/ingest/jobs/{job_id}/start`
- `GET /api/documents`
- `POST /api/documents/search`
- `GET /api/review/edge-candidates`
- `POST /api/review/edge-candidates/{candidate_id}/decision`

MCP endpoint:

- Path: `/mcp`
- Transport: Streamable HTTP
- Exposure: external read-only query tools only

### Environment Variables

`rag/be/.env.example` should include:

```env
OPENROUTER_API_KEY=
RAG_LLM_MODEL=
RAG_EMBEDDING_MODEL=openai/text-embedding-3-large
RAG_EMBEDDING_DIMENSIONS=3072
MEMGRAPH_URI=bolt://localhost:7687
MEMGRAPH_USERNAME=
MEMGRAPH_PASSWORD=
RAG_MCP_HOST=0.0.0.0
RAG_MCP_PORT=8001
RAG_EXTERNAL_MCP_PATH=/mcp
RAG_CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]
RAG_QUERY_TIMEOUT_MS=30000
RAG_QUERY_MAX_ROWS=100
```

Memgraph Docker Compose variables belong under `rag/infra/.env`.

### Reference Implementation Policy

Implementation must prefer official documentation and actual reference code over
blog summaries. Official docs to verify before implementation:

- Memgraph Python client libraries and Neo4j driver compatibility.
- Memgraph text search, vector search, and Cypher query syntax.
- MCP Python SDK FastMCP and Streamable HTTP.
- LangChain tools and MCP adapter behavior.
- LangGraph workflow and tool-calling agent APIs.
- OpenRouter chat and embeddings API.

## 5. Risks & Roadmap

### Technical Risks

- Memgraph does not automatically construct the graph from raw documents.
  Mitigation: own LLM chunking/candidate-generation flow and tests.
- Graph extraction hallucination.
  Mitigation: schema-constrained prompts, source evidence, pending review.
- Legal hierarchy ambiguity.
  Mitigation: explicit hierarchy model and fixtures.
- Embedding/index dimension mismatch.
  Mitigation: centralized settings and startup validation.
- Accidental external writes.
  Mitigation: MCP read-only exposure tests and denied-operation validation.
- Unsafe raw Cypher.
  Mitigation: schema instructions, row/depth/time limits, context-bound writes,
  and audit logs.
- Cost growth from LLM ingest.
  Mitigation: hashing, idempotency, unchanged chunk skipping.

### Phased Rollout

#### MVP: RAG Backend and MCP Backbone

- Run Memgraph and Memgraph Lab through `rag/infra`.
- Implement text ingest API.
- Implement document registration and ingest task/status management.
- Implement agentic ingest backbone from `agentic_ingest_flow_prd.md`.
- Implement external read-only MCP over Streamable HTTP.
- Connect `backend/` only to the external read-only MCP surface.
- Add fixture-based ingest/query tests.

#### v1.1: Review Workflow

- Implement pending candidate review APIs.
- Implement approve/reject/retry workflow.
- Add reviewer note storage and reuse.
- Add hierarchy regression fixtures.

#### v1.2: Query Quality

- Replace temporary `CONTAINS` search with Memgraph text search.
- Improve vector search and graph traversal wrappers.
- Add query service tests from `query_service_tooling_prd.md`.

#### v1.3: Operations UI and Visibility

- Expand `rag/fe` document list, status views, and review queue.
- Add graph visualization roadmap exploration with Memgraph Lab/client support.
- Add structured logs and job audit views.

### Open Decisions

- Final Memgraph schema labels, relationship types, constraints, and indexes.
- Whether `keyword_search` remains as an alias or is deprecated in favor of
  `text_search`.
- Exact OpenRouter chat model for chunking and graph candidate agents.
- Production deployment topology for RAG backend and Memgraph.
