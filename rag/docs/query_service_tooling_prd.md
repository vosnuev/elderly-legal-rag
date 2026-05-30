# Query Service Tooling PRD

## 1. Executive Summary

### Problem Statement

`rag/be/src/query/` is the shared Memgraph query foundation for agentic graph
ingest and the external MCP query surface. Some wrappers are still temporary;
in particular, keyword search currently behaves like a property `CONTAINS` scan
instead of using Memgraph text indexes, so exact legal/domain term search is not
reliable enough.

### Proposed Solution

The query service provides primitive Memgraph query methods that agents can
compose deterministically. Do not collapse text search, vector search, graph
traversal, schema reads, and raw read queries into a single upfront "hybrid
search" tool. Keep those capabilities separate, and let each agent choose the
search route for its current task.

Implementation is split into three boundaries:

- `external/memgraph`: pure Memgraph Bolt client lifecycle and result
  serialization.
- `query/methods`: Memgraph primitive query methods and procedures.
- `query/repositories`: project graph-schema reads/writes for documents, chunks,
  candidates, review notes, and ingest jobs.

### Success Criteria

- Agents can independently compose text, vector, graph traversal, schema, and
  raw read-query primitives.
- Temporary `CONTAINS` search is replaced by Memgraph official text-search
  procedures.
- Query service methods do not create final answers or decide relationship
  candidates.
- Query service methods are not LangChain tools by themselves; `tools/` wraps
  them into agent-facing `@tool` objects with bound context.
- External MCP exposes only read-only query surfaces.

## 2. Scope

### In Scope

- Clarify `rag/be/src/query/` query/search wrapper responsibilities.
- Introduce Memgraph text-search based wrappers.
- Redefine or deprecate the current `keyword_search` behavior.
- Define the minimum responsibility of `probe_existing_context`.
- Align external MCP read-only exposure with internal agent-facing query tools.
- Keep Memgraph Bolt driver lifecycle outside `query/` under `external/memgraph`.

### Out Of Scope

- A vanilla RAG endpoint for final user-answer generation.
- Traditional BM25/vector score-fusion hybrid RAG ranking.
- Graph candidate generation logic.
- LangGraph ingest orchestration.
- Review UI.

## 3. Terminology

### Traditional Hybrid RAG

Traditional hybrid RAG usually combines keyword/BM25-style retrieval and vector
embedding retrieval through score fusion or reranking.

That is not the current graph-ingest target.

### Agentic RAG Query Service

In this project, the query service is a primitive query-method layer that lets an
agent choose its own search route. The agent may use only text search, use vector
search and then graph traversal, read schema first and then write raw read-only
Cypher, or combine multiple primitive methods across turns.

Therefore, the query service must not default to a premature combined search
tool that reduces agent search freedom.

## 4. Query Method Requirements

### `schema_read`

- Reads graph labels, relationship types, index availability, and query
  instructions.
- Why: prevents agents from inventing nonexistent labels, relationships, or
  indexes.

### `read_query`

- Executes bounded read-only Cypher.
- Why: agents need a route for graph reasoning that primitive wrappers cannot
  express.

### `text_search`

- Uses Memgraph official text-search functionality.
- Targets exact legal/domain terms such as law names, ordinance names, article
  numbers, regions, and organization names.
- Why: property `CONTAINS` scanning is temporary and does not satisfy indexed
  search, performance, or accuracy requirements.

### `vector_search`

- Uses Memgraph vector indexes to search chunk/entity embedding similarity.
- Why: agents need to find semantically similar content even when wording
  differs.

### `graph_traverse`

- Reads a bounded neighborhood from a specific node or id.
- Why: after text/vector search finds anchors, agents must inspect legal
  hierarchy, regional scope, and nearby policy context.

### `probe_existing_context`

- A lightweight helper for repeated schema/text/vector/graph-read boilerplate.
- It must not generate candidates, rank candidates for hiding, or create final
  answers.
- Why: repeated boilerplate can be reduced without removing the agent's control
  over the search path.

## 5. Design Rules

- Search tools are read-only.
- Search tools return evidence and context, not final answers.
- Search tools do not create relationship candidates.
- Search tools do not hide candidate possibilities through ranking cutoffs.
- Query service may return scores or match metadata as hints; those values are
  not authoritative confidence.
- A combined search helper can be added only after repeated implementation
  duplication is observed.
- If a combined helper is later added, it must remain decomposable and must not
  replace the primitive tools.
- Write operations are exposed to agents only through purpose-specific,
  context-bound write tools in `tools/`, not through generic search methods.

### Repository Split Rationale

Repositories exist to keep project graph-schema decisions out of primitive query
methods. Text search, vector search, schema reads, and graph traversal are
Memgraph capabilities. `Document`, `Chunk`, `RelationshipCandidate`,
`ReviewNote`, and `IngestJob` are SKN28 graph schema concepts. These two groups
change for different reasons, so they should not live in the same file.

Microsoft GraphRAG uses a similar separation in the local reference repository:

- `reference/graphrag/packages/graphrag/graphrag/query/structured_search/`
  contains query/search algorithms such as local, global, DRIFT, and basic
  search.
- `reference/graphrag/packages/graphrag/graphrag/query/context_builder/`
  assembles context for those algorithms.
- `reference/graphrag/packages/graphrag/graphrag/query/input/retrieval/`
  contains data retrieval helpers for entities, relationships, text units,
  covariates, and community reports.

The practical lesson is not to copy their storage model, but to keep search
strategy, context assembly, and data access as separate responsibilities.

## 6. Tracking Items

### QRY-001: Replace Temporary Keyword Search

- Problem: `keyword_search` currently relies on property string `CONTAINS`
  matching.
- Requirement: implement Memgraph official text-search wrapper.
- Why: exact legal/domain term lookup needs index-backed behavior.

### QRY-002: Clarify Keyword vs Text Naming

- Problem: `keyword_search` and future `text_search` can overlap.
- Requirement: decide whether `keyword_search` becomes an alias, deprecated
  wrapper, or separate exact property search.
- Why: tool names must be clear to agents and external MCP consumers.

### QRY-003: Keep Primitive Methods Exposed

- Problem: a single combined search tool can reduce agentic search freedom.
- Requirement: keep `schema_read`, `read_query`, `text_search`,
  `vector_search`, and `graph_traverse` available independently.
- Why: graph placement is agentic and context-dependent.

### QRY-004: Improve `probe_existing_context`

- Problem: the current helper is too thin for graph placement.
- Requirement: expand only enough to remove repeated boilerplate while preserving
  primitive search control.
- Why: `graph_candidate_agent` should not waste calls on repetitive setup, but it
  must still decide its own search path.

### QRY-005: Permission Boundary Tests

- Problem: query methods serve both external MCP read-only callers and internal
  ingest agents through different wrappers.
- Requirement: tests must verify external read-only behavior and internal
  write-tool isolation.
- Why: accidental external write exposure is a core architecture risk.

## 7. Reference Documentation

- Memgraph text search: https://memgraph.com/docs/querying/text-search
- Memgraph vector search: https://memgraph.com/docs/querying/vector-search
- Memgraph Cypher querying: https://memgraph.com/docs/querying
