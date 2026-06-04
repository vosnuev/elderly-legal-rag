# 20분 발표 슬라이드 구성안 v4

## 핵심 메시지

이 발표의 중심은 "RAG backend 구현"이 아니라, 최종 서비스가 다음 세 영역으로 분리되어 동작한다는 점이다.

> Streaming Frontend는 사용자 경험을 담당하고, Main Backend는 LLM answer runtime을 담당하며, GraphRAG System은 검수 가능한 knowledge graph를 구축한다. Main Backend는 GraphRAG를 직접 수정하지 않고 MCP read-only tool boundary로 조회한다.

v4에서는 실제 Memgraph Lab 화면과 현재 DB count를 넣어, RelationshipCandidate, ReviewNote, Memory가 실제 graph로 연결되어 있다는 점을 mock이 아닌 evidence로 보여준다.

## v4 변경 방향

- Slide 9를 실제 Memgraph Lab graph result 기반으로 교체했다.
  - asset: `presentation/ppt/assets/memgraph-lab-graph-cluster.png`
  - query: `MATCH p=()-[]-() RETURN p`
  - 현재 DB 관측값: 87 nodes, 213 edges, 42 RelationshipCandidate nodes
- Slide 10을 발표용 clean schema/pipeline diagram으로 재구성했다.
  - Memgraph Lab schema auto-layout은 발표용으로 너무 복잡해서 실제 DB count/triplet을 근거로 native diagram으로 다시 렌더링했다.
  - 핵심 구조: `Document -> Chunk`, `Chunk/Document -> RelationshipCandidate`, `RelationshipCandidate -> ReviewNote`, `ReviewNote -> Memory`, approve 이후에만 실제 `Chunk -> Chunk` edge 생성.
- v3의 "GraphRAG 내부 설명" 흐름을 유지하되, 최종 서비스 3분할 구조를 먼저 이해시키는 순서로 정리했다.

## 슬라이드 맵

| # | 시간 | 제목 | 핵심 역할 | 시각 자료 |
| ---: | ---: | --- | --- | --- |
| 1 | 0:45 | Project Thesis | 3계층 GraphRAG 서비스라는 전체 주장 | title + service flow strip |
| 2 | 1:10 | Why Vector-only RAG Is Not Enough | 법령/조례 도메인에서 vector-only 한계 제시 | vector RAG vs reviewable GraphRAG |
| 3 | 1:20 | Data Source and TOON Preprocessing | 데이터 출처와 40.81% 토큰 절감 증명 | API -> JSON -> TOON + token bar |
| 4 | 1:40 | Simplified End-to-End Architecture | 전체 3분할 구조를 먼저 보여줌 | FE / Backend / MCP / GraphRAG / Memgraph |
| 5 | 1:10 | Three System Boundaries | Streaming FE, Main Backend, GraphRAG 책임 분리 | 3-column responsibility map |
| 6 | 1:20 | Streaming Frontend Runtime | token/event stream UX 설명 | frontend stream lifecycle |
| 7 | 1:40 | Main Backend: LLM Chat Runtime | prompt, session, tool call, stream orchestration | actual backend flow image + runtime diagram |
| 8 | 1:30 | Backend to RAG via MCP | answer runtime과 graph construction 분리 | backend -> MCP client -> RAG MCP server |
| 9 | 1:30 | Actual Memgraph Evidence | 실제 DB graph 결과와 node/edge count 증명 | Memgraph Lab screenshot + graph facts |
| 10 | 1:30 | Node/Edge Schema and Construction Pipeline | candidate/review/memory schema와 construction graph 설명 | clean schema + ingest pipeline |
| 11 | 1:30 | Agent Harness and Tool Surface | agent 권한을 context/read/search/write로 제한 | tool surface diagram |
| 12 | 1:40 | Review Queue: Candidate First, Edge Later | 사람이 승인한 candidate만 edge가 됨 | candidate -> review -> edge |
| 13 | 1:30 | Memory Feedback and Observability | review note memory 반영과 Redis event stream | memory loop + observability stream |
| 14 | 1:30 | Validation Plan and Closing | 360 테스트셋, no-tool benchmark, 남은 검증 | actual cost/latency chart + checklist |

## 발표 흐름

1. 법령/조례 RAG는 단순 유사도 검색으로는 부족하다.
2. 최종 서비스는 Streaming Frontend, Main Backend, GraphRAG System으로 분리된다.
3. GraphRAG는 답변을 직접 생성하는 영역이 아니라 검수 가능한 knowledge graph를 만드는 영역이다.
4. Main Backend는 MCP read-only tool을 통해 GraphRAG를 조회한다.
5. LLM agent가 만든 관계는 바로 edge가 아니라 RelationshipCandidate가 된다.
6. 사용자가 Review Queue에서 승인한 후보만 실제 graph edge로 materialize된다.
7. review note는 Memory layer로 갱신되어 다음 candidate generation의 판단 기준에 반영된다.
8. 실제 Memgraph DB에는 candidate, review note, memory, approved edge가 함께 존재한다.
9. 360개 테스트셋과 no-tool benchmark는 확보했고, tool-attached 검증은 다음 단계다.

## 슬라이드 9 발표 포인트

> 이 화면은 발표용 mock이 아니라 Memgraph Lab에서 `MATCH p=()-[]-() RETURN p`를 실행한 실제 graph result입니다. 현재 DB에는 Document 2개, Chunk 35개, RelationshipCandidate 42개, ReviewNote 5개, Memory 1개가 있고, edge는 213개입니다. 여기서 중요한 점은 LLM output이 곧바로 edge가 아니라 candidate와 review note를 거쳐 graph truth로 바뀐다는 점입니다.

## 슬라이드 10 발표 포인트

> DB schema는 candidate와 approved edge를 분리합니다. Document는 Chunk를 가지고, agent는 Chunk를 근거로 RelationshipCandidate를 만듭니다. 사용자의 판단은 ReviewNote로 남고, ReviewNote는 Memory update의 evidence가 됩니다. approve된 후보만 실제 Chunk-to-Chunk edge가 됩니다. construction pipeline의 LangGraph state에는 raw document를 싣지 않고 job_id, document_id, chunk_ids만 흐르게 했습니다.

## 반드시 유지할 문장

> RAG system은 knowledge layer이고, Main Backend는 answer generation runtime입니다. 두 영역은 MCP read-only tool boundary로 분리했습니다.

> LLM은 edge를 확정하지 않습니다. LLM은 RelationshipCandidate만 만들고, 사람의 approve 이후에만 실제 graph edge가 됩니다.

> Memory는 모델 파라미터 학습이 아니라, reviewer note를 바탕으로 다음 agent context에 자동 주입되는 system memory layer입니다.

