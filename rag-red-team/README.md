# RAG Red Team

RAG 파이프라인의 별도 red-team 실험을 위한 루트 디렉토리다. 기존 Agentic RAG가 AI agent로 그래프 후보를 구성하는 방식과 비교하기 위해, 사람이 정리한 청크/엣지 설계 문서와 TOON 원본 데이터를 Neo4j 그래프로 직접 적재한다.

## 구성

```text
rag-red-team/
├── original-data-toon/                 # RAG_PREPROCESSED_DATA에서 복사한 원본 TOON 법령 데이터
├── original-data-with-chunk-and-edge/  # DOCX 기반 청크/엣지 설계 문서
├── original-data-with-chunk-and-edge-md/ # DOCX 설계 문서를 Markdown으로 변환한 검토본
├── infra/               # Neo4j Docker Compose
├── src/                 # 그래프 적재와 MCP 서버 코드
├── Dockerfile           # remote MCP HTTP 서버 컨테이너
├── pyproject.toml
└── .env.example
```

`original-data-toon/`은 법령 원문을 TOON으로 전처리한 실제 원본 데이터다.
`original-data-with-chunk-and-edge/`의 DOCX 파일은 원본 데이터가 아니라, 각 법령 원문을 어떤 단위로 그룹화/청킹하고 어떤 청크끼리 edge를 만들지 사람이 정리한 설계 문서다. 따라서 그래프를 만들 때는 DOCX 파일을 반드시 읽어서 청크와 edge를 구성해야 한다.
`original-data-with-chunk-and-edge-md/`는 같은 DOCX 설계 문서를 Markdown으로 변환한 검토용 사본이며, 현재 그래프 edge 적재의 기준 파일이다.

## 그래프 모델

주요 노드:

- `Document`: TOON 법령 파일 1개에 해당하는 문서 노드
- `Chunk`: TOON `documents[...]` 항목 1개에 해당하는 청크 노드

주요 관계:

- `HAS_CHUNK`: 문서 -> 청크
- `RELATED_TO`: 청크 -> 청크 edge
  - Markdown 설계 문서의 굵은 `조문 -> 조문` 라인을 기준으로 만든 edge
  - `019, 020 -> 021`처럼 source가 여러 개인 설계는 source별 edge로 펼쳐서 적재

## 실행

```bash
cd rag-red-team
cp .env.example .env
uv sync
docker compose -p rag-red-team -f infra/docker-compose.yml up -d
uv run python -m rag_red_team_neo4j.load_graph
```

기본 접속 정보:

```text
Neo4j Browser: http://127.0.0.1:7475
Bolt URI:      bolt://127.0.0.1:7688
User:          neo4j
Password:      1234
Remote MCP:    http://127.0.0.1:9001/mcp
```

적재 검증 예시:

```bash
docker exec rag-red-team-neo4j cypher-shell -u neo4j -p 1234 \
  'MATCH (c:Chunk) RETURN count(c) AS chunks;'
```

현재 데이터 기준 적재 카운트:

```json
{
  "documents": 4,
  "chunks": 388,
  "markdown_chunk_edges": 105,
  "missing_markdown_chunk_edges": 0
}
```

## MCP 서버

stdio transport:

```bash
cd rag-red-team
uv run python -m rag_red_team_neo4j.mcp_server
```

HTTP transport:

```bash
cd rag-red-team
uv run python -m rag_red_team_neo4j.mcp_server --transport http --host 127.0.0.1 --port 9001
```

Docker 기반 remote MCP:

```bash
cd rag-red-team
docker compose -p rag-red-team -f infra/docker-compose.yml up -d --build mcp
```

기본 컨테이너 이름은 `rag-redteam`이고, 컨테이너 내부에서는 `bolt://neo4j:7687`로 Neo4j에 연결한다.

```text
Remote MCP URL: http://127.0.0.1:9001/mcp
Container:      rag-redteam
```

FastMCP CLI로 직접 확인:

```bash
uv run fastmcp list mcp_server.py
uv run fastmcp call mcp_server.py graph_schema --json
uv run fastmcp call mcp_server.py search_chunks \
  --input-json '{"keyword":"고령자","limit":2}' \
  --json
```

HTTP MCP 서버가 떠 있는지 확인:

```bash
docker logs rag-redteam --tail=50
docker compose -p rag-red-team -f infra/docker-compose.yml ps
```

도구:

- `graph_schema`: label/relationship count와 예시 쿼리 반환
- `run_cypher`: read-only Cypher 실행
- `search_chunks`: 키워드 기반 청크 검색
- `manual_relations`: Markdown 설계 문서 기반 관계 조회

`run_cypher`는 `CREATE`, `MERGE`, `SET`, `DELETE`, `DROP`, `CALL` 등 쓰기나 procedure 실행 가능성이 있는 키워드를 차단한다. Neo4j driver도 read routing으로 실행한다.

예시 read-only Cypher:

```cypher
MATCH p=(a:Chunk)-[r:RELATED_TO]->(b:Chunk)
RETURN p
LIMIT 200
```

문서 간 edge만 확인:

```cypher
MATCH p=(a:Chunk)-[r:RELATED_TO]->(b:Chunk)
WHERE a.document_name <> b.document_name
RETURN p
LIMIT 100
```

문서쌍별 edge 수 확인:

```cypher
MATCH (a:Chunk)-[r:RELATED_TO]->(b:Chunk)
RETURN a.document_name AS source_document,
       b.document_name AS target_document,
       count(r) AS edges
ORDER BY edges DESC, source_document, target_document
```

청크 edge를 표로 확인:

```cypher
MATCH (a:Chunk)-[r:RELATED_TO]->(b:Chunk)
RETURN a.document_name, a.chunk_key, r.edge_line, r.relation_type,
       coalesce(r.curation_method, 'markdown') AS curation_method,
       b.document_name, b.chunk_key, r.summary
LIMIT 10
```

## 종료

```bash
cd rag-red-team
docker compose -p rag-red-team -f infra/docker-compose.yml down
```

데이터까지 지우려면:

```bash
docker compose -p rag-red-team -f infra/docker-compose.yml down -v
```
