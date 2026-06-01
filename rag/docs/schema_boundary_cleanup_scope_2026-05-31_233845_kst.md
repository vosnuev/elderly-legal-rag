# Schema Boundary Cleanup Scope

Recorded at: 2026-05-31 23:38:45 KST

## Purpose

This note records the current cleanup scope before changing implementation code.
The immediate goal is not to reuse or patch overbuilt code. The goal is to
identify what should be cut, what should be moved, and where each schema
boundary belongs.

Import errors are acceptable during the upcoming hard cleanup if they are caused
by intentionally removing the wrong abstraction first.

## Core Boundary Decision

The RAG backend has three different schema categories. They must not live in the
same file.

1. Database storage schema
   - Owns the Memgraph node and relationship shape.
   - Should live under `be/src/query/schema/`.
   - This layer should describe persisted graph objects such as original
     document nodes, chunk nodes, relationship candidate nodes, review note
     nodes, and materialized relationship metadata.
   - This schema is not an agent prompt schema and not a FastAPI request schema.

2. Tool schema
   - Owns LangChain tool argument schemas.
   - Can remain beside each tool implementation, such as
     `be/src/tools/chunk_tools.py` and `be/src/tools/candidate_tools.py`.
   - This schema is the input contract exposed to agents.
   - Tool schemas should be derived from or adapted to the database storage
     schema, but they should not expose database-generated technical fields as
     agent-written fields.

3. Graph runtime state
   - Owns LangGraph state passed between graph nodes.
   - Should live in `be/src/pipeline/state.py`.
   - State should stay id-centric: `job_id`, `document_id`, `chunk_ids`,
     `edge_candidate_ids`, phase markers, and minimal graph-control fields.
   - Raw documents, full chunk objects, candidate objects, warnings, errors, and
     feedback payloads should not be carried as shared agent context.

## Current Files That Are Overloaded

### `be/src/pipeline/schemas.py`

This file currently mixes unrelated schema categories:

- `RegisteredDocument`: database `Document` node shape.
- `GraphChunk`: database `Chunk` node shape plus embedding fields.
- `RelationshipCandidate`: database edge-candidate node shape.
- `FeedbackJudgeResult`: agent or graph result DTO.
- `ReviewDecisionRequest`: API request DTO.
- `IngestGraphResult`: graph/job result DTO.
- `GraphIngestPhase` and `ReviewAction`: workflow enums.

This file should be split. Database node schemas should move to the future
`query/schema/` layer. Runtime graph result DTOs and phase enums can remain in a
pipeline-owned schema module or be split into a more explicit runtime/result
module. API request DTOs should not live here if they are only used at API or
ingestion boundaries.

### `be/src/tools/context.py`

This file introduces hidden `ContextVar` based state:

- `job_id`
- `agent_name`
- `operation_scope`
- `document_id`
- `chunk_id`
- `candidate_id`
- bound raw document content

This is now considered overbuilt for the current direction. The agent/tool
boundary should not hide job or document identifiers in implicit runtime
context. `job_id` belongs to the ingestion worker/pipeline layer, not to an
agent tool argument schema. Agent-visible tools should either receive explicit
database identifiers in their tool arguments or use query tools to read graph
state by id.

`tools/context.py` is therefore a primary cut target.

### `be/src/tools/chunk_tools.py`

This file is in the right general location for tool schemas, but the current
tool schema is not aligned with the database-id ownership rule.

Current issue:

- `ChunkWriteInput.id` asks the agent to provide a stable chunk id.

Target direction:

- The tool or database write layer should create the chunk id when saving.
- The tool result should return generated `chunk_ids`.
- The agent should provide semantic chunk content and source-boundary data, not
  database technical identifiers.

The tool schema can stay in this file, but it should adapt to the future
database `Chunk` storage schema and exclude generated technical fields from
agent input.

### `be/src/tools/candidate_tools.py`

This file is also in the right general location for relationship edge-candidate
tool schemas, but it has the same id ownership problem.

Current issue:

- `EdgeCandidateWriteInput.id` asks the agent to provide a stable relationship
  candidate id.

Target direction:

- The tool or database write layer should create the edge-candidate id when
  saving.
- The tool result should return generated `edge_candidate_ids`.
- The agent should provide the proposed source node, target node, relationship
  type, evidence, rationale, source chunk reference, and metadata that are
  semantic to the graph construction task.

The candidate here means an edge candidate, not a chunk candidate.

## Current Files That Are Partially Aligned

### `be/src/pipeline/state.py`

This file is already moving in the correct direction because
`GraphIngestState` is mostly id-centric:

- `job_id`
- `document_id`
- `chunk_ids`
- `edge_candidate_ids`
- `missing_chunk_ids`
- `phase`

The remaining review action state still carries candidate dictionaries and
warnings/errors. That may be acceptable for the separate review graph for now,
but it should be reviewed after database schema boundaries are fixed.

### `be/src/ingestion/schemas.py`

This file is suitable for ingestion/API/job-facing schemas:

- upload request DTOs
- FE-facing ingest status DTOs
- ingest stage enums
- search request/response DTOs used by FE operations

It should not become the database graph schema layer.

### `be/src/query/write/document_registration.py`

This is the one deterministic write that remains outside the agentic write
tools: original uploaded document registration. It writes the initial
`Document` node before the graph construction pipeline starts.

The document write should eventually consume the database `Document` schema from
`query/schema/`, but the existence of this deterministic write is still valid.

## Implied Database Schema Sources In Current Code

The current database schema is implicit and scattered across these files:

- `be/src/pipeline/schemas.py`
- `be/src/query/write/document_registration.py`
- `be/src/tools/chunk_tools.py`
- `be/src/tools/candidate_tools.py`
- `be/src/pipeline/services/embedding_dispatch_service.py`
- `be/src/pipeline/services/actual_edge_materialization_service.py`
- `be/src/pipeline/services/review_status_service.py`
- `be/src/pipeline/services/preference_memory_service.py`
- `be/src/pipeline/services/ingest_progress_service.py`

Before tool cleanup, the persisted graph shapes should be made explicit under
`query/schema/`.

## Cut Targets

1. Remove `tools/context.py` and its hidden context binding model.
2. Remove `AgentToolContext` exports from `tools/__init__.py`.
3. Stop tool implementations from relying on context-bound job/document/chunk
   ids.
4. Stop asking agents to generate database ids for chunks and edge candidates.
5. Split `pipeline/schemas.py` so DB entities no longer live in pipeline
   runtime schema.
6. Keep import breakage acceptable during the hard cut, then repair call sites
   after the schema and tool boundaries are clear.

## Proposed Next Refactor Order

1. Add `be/src/query/schema/` for Memgraph storage contracts.
2. Move or redefine database storage schemas there:
   - `Document`
   - `Chunk`
   - `RelationshipCandidate` or `EdgeCandidate`
   - `ReviewNote`
   - `IngestJob` progress node, if it remains persisted in Memgraph
3. Trim `be/src/pipeline/schemas.py` to pipeline result and workflow DTOs only,
   or split result DTOs into a clearer pipeline runtime module.
4. Update tool schemas to be agent input schemas beside each tool, adapting to
   the DB storage schemas and excluding generated ids.
5. Remove `tools/context.py` and update affected tools to explicit arguments or
   direct query-layer calls.
6. Update agents after the tool boundary is fixed.
7. Update pipeline services that currently imply DB shape through raw Cypher.

## Non-Goals For This Cleanup Step

- Do not implement agent streaming or observability yet.
- Do not add blob/S3-style log dumping yet.
- Do not run the agent graphs yet.
- Do not preserve overbuilt context abstractions just to keep current imports
  green.
- Do not move tool schemas away from tool files unless they become database
  storage schemas.
