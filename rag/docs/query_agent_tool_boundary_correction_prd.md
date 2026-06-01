# Query-Agent Tool Boundary Correction PRD

## 1. Executive Summary

### Problem Statement

The current RAG backend mixes responsibilities across the Memgraph query layer,
graph ingest subagent tools, and actual database write points. In particular,
`dry_run` and `job_id` are exposed as agent-facing tool parameters, which forces
the LLM to construct runtime execution context that should already be owned by
the orchestrator or task layer.

### Proposed Solution

Move the Neo4j-compatible Bolt client code out of `query/client.py` and into an
external Memgraph adapter boundary under `external/memgraph`. Keep `query/` as
the Memgraph query method and repository layer. Define singleton LangChain
`@tool` objects under `tools/`, where execution context is bound before tools
are used by subagents.

### Success Criteria

- Agent-facing tool schemas do not expose `job_id`, task id, `dry_run`, mock, or
  no-op controls.
- Runtime ingest writes are real execution paths, not default no-op previews.
- The Memgraph Bolt adapter contains no job/task/progress/agent policy concepts.
- Each graph record type has one explicit write owner.
- External MCP exposes read-only tools only.
- Tests verify subagent tool schemas, tool access groups, and MCP exposure.

## 2. Current State Assessment

### Current Components

| Area | Current Role | Issue |
| --- | --- | --- |
| `be/src/query/client.py` | Connects to Memgraph through a Neo4j-compatible Bolt driver and executes queries. | This is an external Memgraph Bolt adapter, not a query business layer. |
| `be/src/query/read`, `be/src/query/write` | Holds direct database query functions. | Query functions must stay database-query only and must not contain prompts, MCP registration, or runner policy. |
| `be/src/query/guard.py` | Removed. | Token-scanning guard files do not belong in the query layer. |
| `chunking_agent` tools | Expose read/write/upsert tools directly. | The LLM is asked for `job_id` and `dry_run`, even though the orchestrator already owns context. |
| `graph_candidate_agent` tools | Expose raw read/write/search/traversal/candidate store tools. | Candidate persistence must be owned by context-bound agent write tools, not duplicated by service nodes. |
| `review_resume_agent` | Generates a new candidate version after retry. | The name is ambiguous; the agent revises candidates, it does not resume all review logic. |
| service nodes | Persist documents, embeddings, progress, review actions, and actual edge materialization. | They must not duplicate chunk or relationship candidate writes owned by agent tools. |

### Official Documentation Basis

- Memgraph supports the Neo4j Python client and GQLAlchemy. Memgraph and Neo4j
  both support Bolt protocol and Cypher queries:
  https://memgraph.com/docs/client-libraries/python
- Memgraph read/query basics use Cypher clauses such as `MATCH`, `WHERE`,
  `RETURN`, `UNWIND`, and relationship pattern traversal:
  https://memgraph.com/docs/querying/read-and-modify-data
- Memgraph runtime schema tracking exposes `SHOW SCHEMA INFO`, which returns
  nodes, edges, indexes, constraints, and enums when `--schema-info-enabled` is
  enabled:
  https://memgraph.com/docs/querying/schema
- Memgraph text search uses text indexes and the `text_search.search()` /
  `text_search.search_edges()` procedures:
  https://memgraph.com/docs/querying/text-search
- Memgraph vector search uses vector indexes and the `vector_search.search()` /
  `vector_search.search_edges()` procedures:
  https://memgraph.com/docs/querying/vector-search
- LangChain tools can be defined with `@tool` and passed to `create_agent`, so
  reusable imported tool registries are valid:
  https://docs.langchain.com/oss/python/langchain/tools

### Target Query Method Categories

The query layer should expose Memgraph query methods as data interaction
capabilities, not as agent policy.

| Query Method | Official Basis | Target Wrapper Responsibility |
| --- | --- | --- |
| Cypher read and repository writes | Memgraph Cypher read/modify clauses | Execute bounded read queries and purpose-specific repository mutations through the external Memgraph adapter. |
| Schema read | `SHOW SCHEMA INFO` | Return Memgraph-tracked schema instead of manually scanning labels and relationship types. |
| Text search | `text_search.search`, `text_search.search_edges` | Execute indexed full-text search; replace temporary property `CONTAINS` scans. |
| Vector search | `vector_search.search`, `vector_search.search_edges` | Execute indexed semantic search over node/edge embeddings. |
| Graph traversal | Cypher relationship patterns and bounded path traversal | Execute bounded neighborhood/path queries around anchors while allowing agents to use `read_query` for custom traversal Cypher. |

### Specific Problems

#### `dry_run`

`dry_run` is not a runtime ingest tool parameter.

Current problems:

- Runtime write/upsert style tool surfaces can drift into no-op behavior if
  preview execution is mixed into production code.
- Exposing `dry_run` in the tool schema asks the model to decide execution
  policy.
- Preview behavior and production ingest writes are mixed in the same tool.

Correction:

- Remove `dry_run` from all runtime subagent tools.
- If preview mode is needed later, design it as a separate maintenance or
  evaluation interface.
- Remove mock/no-op tool paths from production runtime code.

#### `job_id`

`job_id` is needed for audit and lineage, but the LLM must not provide it.

Current problems:

- `job_id` is already present in `GraphIngestState` and orchestrator context.
- Broad write tools can expose `job_id` again even though context already owns
  it.
- A model-provided `job_id` can break lineage, and missing values currently fail
  in validation.

Correction:

- Bind `job_id` through an `AgentToolContext` created by the orchestrator or graph
  node.
- Do not expose `job_id` in LLM-facing tool schemas.
- Persistence methods should record `job_id` from bound context.

#### Raw Write Query Exposure

Subagents may need write capability, but not a broad generic write tool.

Current problems:

- A generic raw write tool is too wide for subagent use.
- A broad DB write permission does not identify the target graph object or
  invariant.
- Token-level Cypher validation does not enforce domain-level rules.

Correction:

- Prefer purpose-specific write tools.
- Do not keep a generic raw write query service method in the runtime path.
- Do not expose `job_id`, `purpose`, or `dry_run` as LLM parameters.

## 3. User Experience & Functionality

### User Personas

- RAG backend developer: maintains safe boundaries between query, tools,
  persistence, and task execution.
- RAG ingest agent designer: designs subagent prompts and tool schemas.
- RAG operator: reviews document ingest status and relationship candidates.

### User Stories

#### Story 1: Context-Bound Agent Tools

As a RAG ingest agent designer, I want subagent tools to receive execution
context from the orchestrator so that the LLM does not invent `job_id`,
`document_id`, or runtime policy flags.

Acceptance Criteria:

- `chunking_agent`, `graph_candidate_agent`, and candidate revision tools do not
  expose `job_id`.
- Runtime tools do not expose `dry_run`, mock, preview, or no-op flags.
- Tool implementations use bound context for `job_id`, `document_id`,
  `chunk_id`, and `candidate_id`.

#### Story 2: Clear DB Write Ownership

As a RAG backend developer, I want each graph record type to have one write owner
so that agent output and service node persistence do not conflict.

Acceptance Criteria:

- `Document` writes are owned by `ingest_tasks.document_service`.
- `Chunk` writes are owned by `chunking_agent` through context-bound chunk write
  tools.
- `RelationshipCandidate` writes are owned by `graph_candidate_agent` and
  `graph_candidate_revision_agent` through context-bound candidate write tools.
- Service nodes do not persist agent-generated chunks or relationship candidates.
- Review decision, actual edge materialization, and review note writes have one
  explicit owner.

#### Story 3: Read-Only External MCP

As a backend main agent integrator, I want external MCP tools to stay read-only
so that user-facing agent queries cannot mutate Memgraph.

Acceptance Criteria:

- `api/mcp.py` registers no write tools.
- MCP exposure tests assert that write/upsert/store/materialize/review tools are
  absent.
- Internal subagent write tools are never registered in FastMCP.

#### Story 4: Clear Candidate Retry Agent Naming

As a maintainer, I want retry-agent names to describe candidate revision work so
that graph names and code navigation are unambiguous.

Acceptance Criteria:

- `review_resume_agent` is renamed to `graph_candidate_revision_agent`.
- `review_resume_graph` is renamed to `candidate_review_action_graph`.
- `ReviewResumeState` is renamed to `CandidateReviewActionState`.
- Public API names may keep review decision terminology, but internal agent names
  must describe candidate revision.

### Non-Goals

- Improving Memgraph text/vector search ranking quality.
- Designing candidate grouping or reviewer note UX.
- Expanding external MCP beyond read-only query tools.
- PDF/VLM ingest.
- Mock tool framework or dry-run preview console.

## 4. AI System Requirements

### Tool Requirements

Subagent tools must be separated across adapter, query service, tool module,
and task runtime layers.

| Layer | Visibility | Owner | Rule |
| --- | --- | --- | --- |
| Memgraph external adapter | Internal Python only | `external/memgraph` | Pure Bolt driver connection and query execution. No job/task/agent policy. |
| Query method service | Internal Python only | `query/` | Memgraph read/write database query methods. No LangChain `@tool`. |
| Agent tool module | Internal agent only | `tools/` | Singleton LangChain `@tool` objects, access composition, context binding. |
| API/MCP exposure | External callers | `api/` | MCP read-only exposure only. No internal write tools. |

Tool module requirements:

- `tools/` exports reusable singleton `@tool` objects through `tools/__init__.py`.
- Subagents import named tools directly instead of resolving tools through
  a string-name lookup layer.
- Tool composition must be explicit: read-only, chunk-write, candidate-write,
  and review-context tools are selected by each subagent.
- Tests must whitebox-check exact tool exposure for each agent.
- Token-scanning guard files must not be used as the main agent access policy.
  External MCP receives read tools only; internal write tools are not registered
  in MCP.

### Evaluation Strategy

- Tool schema test: internal subagent tools must not expose `job_id` or
  `dry_run`.
- Tool schema test: runtime tools must not expose mock/no-op/preview parameters.
- MCP exposure test: external MCP surface must not contain write-capable tools.
- Tool access test: each subagent tool list exactly matches its allowed tool
  groups.
- Persistence ownership test: one graph entity type is not written by both an
  agent tool and a service node in the same flow.
- Audit test: persisted write records include `job_id` from bound context.
- Negative test: broad raw write query is absent from runtime tool and query
  service surfaces.

## 5. Technical Specifications

### Target Architecture

```text
FastAPI API
  -> ingest_tasks
       -> document_service writes Document + IngestJob
       -> task_queue starts graph ingest with job_id/document_id
  -> pipeline.pipeline
       -> builds AgentToolContext
       -> imports singleton tools from tools/
       -> runs subagents with context-bound tools
       -> runs service nodes only for records they own
  -> tools/
       -> singleton LangChain @tool objects and access composition
  -> query/
       -> methods: Memgraph query method wrappers
       -> methods/write: internal database write query methods
       -> validation helpers only after access is decided
  -> external/memgraph
       -> pure Memgraph Bolt driver adapter
  -> Memgraph
```

### External Memgraph Adapter Boundary

Target location:

```text
be/src/external/memgraph/
```

Responsibilities:

- Own Neo4j-compatible driver import and `GraphDatabase.driver(...)` setup.
- Execute read/write Cypher with parameters.
- Serialize driver records, nodes, relationships, paths, and counters.
- Verify connectivity and close the driver.

Non-responsibilities:

- `job_id`, task id, ingest progress, audit lineage.
- Agent name, tool name, permission groups.
- Document/chunk/candidate domain decisions.
- Dry-run, mock, or placeholder execution.

### Query Service Boundary

Target location:

```text
be/src/query/
├── methods/read/
│   ├── raw.py
│   ├── schema.py
│   ├── text_search.py
│   ├── vector_search.py
│   └── traversal.py
├── methods/write/
│   ├── document_write.py
│   ├── chunk_write.py
│   ├── relationship_candidate_write.py
│   ├── review_note_write.py
│   └── ingest_job_write.py
├── service.py
└── utils.py
```

Responsibilities:

- Provide Memgraph query method wrappers:
  - Cypher read/write execution over the external adapter.
  - Text search using Memgraph text search procedures.
  - Vector search using Memgraph vector search procedures.
  - Bounded graph traversal using Cypher path patterns.
- Provide domain repository methods as implementation behind API, tool, and
  service boundaries, without exposing them directly as external MCP tools.
- Keep query result normalization close to DB access.

Non-responsibilities:

- LangChain `@tool` definitions.
- Agent access policy.
- Task queue state.
- Runtime `job_id` decisions.
- Dry-run or mock behavior.
- Neo4j driver lifecycle.

### Agent Tool Registry Boundary

Target location:

```text
be/src/tools/
```

Responsibilities:

- Define reusable singleton LangChain `@tool` wrappers.
- Bind `AgentToolContext` before a tool is invoked by an agent.
- Group tools by access class and agent role.
- Provide whitebox tests for exact tool exposure.

Possible package shape:

```text
be/src/tools/
├── __init__.py
├── context.py
├── memgraph_read_tools.py
├── chunk_tools.py
├── candidate_tools.py
└── review_context_tools.py
```

Rules:

- Agent files import named singleton tools from `tools/`; agent files keep
  prompts and agent assembly.
- `tools/` must not require a string-name lookup layer for normal subagent
  composition.
- Runtime tool schemas contain no `job_id`, task id, `dry_run`, mock, preview,
  or no-op flags.
- Write tools are purpose-specific and context-bound.

### Ingest Task Boundary

`ingest_tasks/` owns task submission and progress checking. This is separate
from Memgraph query method access.

Responsibilities:

- Create ingest job/task identifiers.
- Register the original document before graph construction starts.
- Submit graph construction to the orchestrator.
- Store/check job progress and completion state.

Non-responsibilities:

- Neo4j driver connection.
- Agent tool access policy.
- Memgraph query method implementation.
- LLM prompt/tool schema design.

### Agent Tool Context

Add a runtime context object for internal graph ingest tools.

Required fields:

- `job_id`
- `document_id` when document-scoped
- `chunk_id` when chunk-scoped
- `candidate_id` when review/candidate-scoped
- `agent_name`
- `operation_scope`

Rules:

- Context is constructed by the orchestrator or graph node.
- Context is never generated by the LLM.
- Singleton tools read bound runtime context and expose only semantic parameters to the
  LLM.

### DB Interaction Ownership Matrix

| Graph Object | Target Owner | Notes |
| --- | --- | --- |
| `Document` | `ingest_tasks.document_service` | Original raw content is stored before graph ingest starts. |
| `IngestJob` | `ingest_tasks` + `ingest_progress_service` | Job creation and progress updates are deterministic context writes. |
| `Chunk` | `chunking_agent` through context-bound `write_chunk_tool` | Agent creates and writes chunk records with bound job/document context. |
| `Chunk.embedding` | `embedding_dispatch_service` | Embedding worker writes model/dim/status/vector. |
| `RelationshipCandidate` | `graph_candidate_agent` and `graph_candidate_revision_agent` through context-bound candidate write tools | Agent creates and writes candidate records with bound job/document/chunk/candidate context. |
| approved actual edge | `actual_edge_materialization_service` | Triggered only by explicit yes action. |
| rejected/retry status | `review_status_service` | Triggered only by explicit no/retry action. |
| retry candidate version | `graph_candidate_revision_agent` through context-bound tool | Uses reviewer note and original candidate context. |
| `ReviewNote` | `preference_memory_service` | Created from UI/user note, not invented by the agent. |

### Naming Corrections

| Current Name | Target Name | Reason |
| --- | --- | --- |
| `review_resume_agent` | `graph_candidate_revision_agent` | Revises a relationship candidate after retry. |
| `ReviewResumeAgent` | `GraphCandidateRevisionAgent` | Class name must match role. |
| `review_resume_agent.py` | `graph_candidate_revision_agent.py` | File name must match class/agent role. |
| `review_resume_graph` | `candidate_review_action_graph` | Graph handles yes/no/retry review actions. |
| `ReviewResumeState` | `CandidateReviewActionState` | State name should describe the action flow. |
| `_run_review_resume_agent` | `_run_graph_candidate_revision_agent` | Orchestrator node name should match agent role. |

### Required Code Changes

1. Add `AgentToolContext`.
2. Refactor subagent tools to use bound runtime context.
3. Move Memgraph Bolt driver code from `query/client.py` to `external/memgraph`.
4. Refactor `query/` into Memgraph query method and domain repository
   boundaries.
5. Add `tools/` singleton tool layer with context-bound runtime execution.
6. Remove `job_id`, task id, `dry_run`, mock, preview, and no-op flags from all
   runtime agent-facing tool schemas.
7. Remove runtime dry-run/mock execution paths instead of preserving them behind
   flags.
8. Remove service-owned chunk and relationship-candidate persistence paths from
   the graph flow.
9. Rename `review_resume_agent` to `graph_candidate_revision_agent`.
10. Update tests and PRDs to reflect corrected boundaries.

## 6. Risks & Roadmap

### Technical Risks

- Removing `dry_run` from runtime tools can cause accidental writes if tool
  composition is wrong.
  - Mitigation: tests must verify exact tool visibility and schemas.
- Reintroducing a broad raw write query can become too permissive.
  - Mitigation: keep writes behind purpose-specific context-bound tools and
    repository methods.
- Agent-owned writes for chunks/candidates may complicate idempotency.
  - Mitigation: require deterministic IDs and merge keys in tool implementation.
- Service nodes may accidentally reintroduce duplicate chunk/candidate writes.
  - Mitigation: add ownership tests and keep chunk/candidate persistence behind
    context-bound agent write tools only.

### Phased Rollout

#### MVP Correction

- Rename retry agent and graph/state names.
- Add `AgentToolContext`.
- Move Memgraph Bolt client adapter under `external/memgraph`.
- Add `tools/` singleton tool layer and import tools from subagent files.
- Remove `job_id`, task id, `dry_run`, mock, preview, and no-op controls from
  subagent tool schemas.
- Keep external MCP read-only.
- Add tests for tool schema, subagent tool access, and MCP exposure.

#### v1.1 Boundary Cleanup

- Split query service responsibilities or move domain persistence into
  repository-style modules.
- Remove duplicate chunk/candidate write ownership.
- Add audit log assertions for bound `job_id`.
- Replace temporary property `CONTAINS` text search with Memgraph text index
  procedure usage.

#### v1.2 Runtime Hardening

- Add stronger read-query guardrails.
- Add graph mutation audit records.
- Add fixture-based ingest flow tests against a disposable Memgraph instance.
