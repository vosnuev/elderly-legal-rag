# 20분 발표 슬라이드 구성안 v3

## 핵심 메시지

이 발표는 RAG backend 내부 구현 설명에서 시작하지 않는다. 먼저 최종 서비스가 세 영역으로 분리되어 동작한다는 점을 보여준다.

> Streaming Frontend는 사용자 경험을 담당하고, Main Backend는 LLM answer runtime을 담당하며, GraphRAG System은 검수 가능한 knowledge graph를 구축한다. Main Backend는 GraphRAG를 직접 수정하지 않고 MCP read-only tool boundary로 조회한다.

## v3 변경 방향

- 초반에 `Simplified End-to-End Architecture`를 넣어 전체 서비스 흐름을 먼저 잡는다.
- `Evaluation Targets` 단독 슬라이드는 제거하고 마지막 validation 슬라이드에 흡수한다.
- 기존 RAG 내부 구조 설명은 뒤로 이동한다.
- mock UI처럼 보이던 요소를 줄이고, artifact-tool native shape 기반의 diagram-as-code 렌더링으로 재구성한다.
- 실제 이미지 asset이 있는 항목은 PPT에 실제 이미지를 삽입한다.
  - `backend/flow.PNG`
  - `presentation/test-data/no-tool-benchmark/charts/cost_vs_latency_scatter.png`

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
| 9 | 1:30 | GraphRAG System Boundary | RAG admin/API/worker/Memgraph/MCP 역할 | RAG internal boundary diagram |
| 10 | 1:30 | Async Ingest and Construction Graph | document upload부터 candidate 생성까지 | job queue + LangGraph DAG |
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
8. 360개 테스트셋과 no-tool benchmark는 확보했고, tool-attached 검증은 다음 단계다.

## 반드시 유지할 문장

> RAG system은 knowledge layer이고, Main Backend는 answer generation runtime입니다. 두 영역은 MCP read-only tool boundary로 분리했습니다.

> LLM은 edge를 확정하지 않습니다. LLM은 RelationshipCandidate만 만들고, 사람의 approve 이후에만 실제 graph edge가 됩니다.

> Memory는 모델 파라미터 학습이 아니라, reviewer note를 바탕으로 다음 agent context에 자동 주입되는 system memory layer입니다.

