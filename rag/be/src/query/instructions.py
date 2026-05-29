from __future__ import annotations

GRAPH_SCHEMA_INSTRUCTIONS = """
This is an agentic GraphRAG Memgraph tool server.

External tools are read-only. Write operations are rejected.
Internal tools are for the RAG ingest / graph construction agent only.

Core graph hierarchy:
- (:Law)-[:DELEGATES_TO]->(:Ordinance)
- (:Ordinance)-[:HAS_ENFORCEMENT_RULE]->(:EnforcementRule)
- (:Ordinance)-[:APPLIES_TO_REGION]->(:Region)
- (:EnforcementRule)-[:APPLIES_TO_REGION]->(:Region)
- (:Document)-[:HAS_CHUNK]->(:Chunk)
- (:Chunk)-[:MENTIONS]->(:Entity)
- (:Chunk)-[:EVIDENCE_FOR]->(:RelationshipCandidate)

Prefer wrapper tools for vector search, keyword search, graph traversal, and schema reads.
Use raw Cypher only when wrapper tools cannot express the graph reasoning.
Always bound query result size and traversal depth.
"""
