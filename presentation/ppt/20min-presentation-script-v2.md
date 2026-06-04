# 20분 발표 슬라이드 구성안 v2

## 발표 제목

검수 가능한 GraphRAG: 법령/조례 문서를 지식 그래프로 구축하고 MCP로 활용하는 RAG 시스템

## v2 반영 상태

이번 버전은 발표에 바로 넣을 수 있는 근거가 확보된 항목과 아직 남은 검증 항목을 분리한다.

| 상태 | 항목 | 근거 위치 |
| --- | --- | --- |
| 채워짐 | RAG 원천/전처리 데이터 위치 정리 | `rag/RAG_ORIGINAL_DATA`, `rag/RAG_PREPROCESSED_DATA` |
| 채워짐 | red-team용 원본 법령 문서 4개 다운로드 | `rag-red-team/original-data/*.docx` |
| 채워짐 | 대표 질문/평가 질문 360개 테스트 셋 | `presentation/test-data/rag-agent-question-cases/rag_agent_question_test_cases_360.md` |
| 채워짐 | no-tool 모델/provider raw benchmark 결과 | `presentation/test-data/no-tool-benchmark/raw-results/*.csv` |
| 채워짐 | no-tool benchmark 요약/차트 | `presentation/test-data/no-tool-benchmark/artifacts`, `presentation/test-data/no-tool-benchmark/charts/cost_vs_latency_scatter.png` |
| 채워짐 | 환각 방지/출처 품질의 설계 근거 | `backend/src/prompt/system_prompt.j2`, 360개 테스트 케이스의 edge/special case |
| 남음 | MCP tool을 붙인 상태의 동일 테스트셋 재실행 | tool-attached benchmark runner 필요 |
| 남음 | retrieval quality와 citation grounding 자동 채점 | with-tool 결과 생성 후 judge/eval 필요 |

Raw result 위치 정리:

- `presentation/test-data/no-tool-benchmark/raw-results/*.csv`: provider별 생 실행 결과다. 각 파일은 360개 테스트 케이스에 대한 답변, token, cost, latency, routing, status, error를 포함한다.
- `presentation/test-data/no-tool-benchmark/artifacts/*.csv`: raw result를 합치거나 provider/question/segment 단위로 요약한 파생 산출물이다.
- `presentation/test-data/no-tool-benchmark/results/benchmark_all_model_by_provider.xlsx`: 발표/분석용 엑셀 결과 묶음이다.
- `presentation/test-data/no-tool-benchmark/charts/cost_vs_latency_scatter.png`: 발표에 우선 포함할 cost/latency 산점도다. `latency_distribution_boxplot.png`는 이번 20분 발표 본문에서는 제외한다.

## 발표 시간 배분

총 20분 기준이다. 실제 설명은 약 17분 15초로 잡고, 마지막 2분 45초는 전환 지연, 데모 화면 대기, Q&A에 남긴다.

| 구간 | 시간 | 목적 |
| --- | ---: | --- |
| 문제 정의와 평가 기준 대응 | 3분 5초 | 왜 단순 vector RAG가 부족한지, 무엇을 만들었는지 선언한다. |
| 데이터 출처와 전처리 | 1분 30초 | 수집 근거와 TOON 전처리 효과를 숫자로 보여준다. |
| 시스템 아키텍처 | 5분 50초 | RAG backend, task queue, worker, Memgraph, MCP boundary를 설명한다. |
| Human-in-the-loop와 Memory | 4분 30초 | RelationshipCandidate, Review Queue, Memory feedback loop를 설명한다. |
| 최종 Q&A 활용과 검증 계획 | 2분 20초 | MCP 기반 질의응답 runtime과 테스트 계획을 정리한다. |
| 마무리/Q&A | 2분 45초 | 핵심 차별점과 다음 검증 작업을 짧게 재강조한다. |

## 한 줄 주장

이 프로젝트는 문서를 벡터 DB에 넣고 검색하는 데서 끝나는 RAG가 아니라, LLM agent가 관계 후보를 만들고 사람이 검수한 뒤 실제 knowledge graph로 확정하는 GraphRAG 구축 시스템이다.

## 발표 스토리라인

1. 법령/조례 기반 질의응답은 단순 유사도 검색만으로 부족하다.
2. 그래서 문서를 chunk로 나누고 embedding만 저장하는 대신 Memgraph 기반 그래프 구조를 만든다.
3. LLM agent가 관계를 바로 확정하지 않고 `RelationshipCandidate`로 제안한다.
4. 사용자는 Review Queue에서 후보를 승인/거절하고, 승인된 후보만 실제 edge가 된다.
5. 사용자의 review note는 Memory layer로 업데이트되어 다음 candidate generation에 반영된다.
6. 구축된 graph는 read-only MCP server로 외부 agent와 최종 Q&A backend에 제공된다.
7. 테스트는 모델 비교, 근거 기반 답변, 문서 외 질문 환각 방지, tool call 안정성을 기준으로 정리한다.

## 디자인 방향

- 톤: 기술 데모이지만 발표용으로는 "검수 가능한 자동화"를 전면에 둔다.
- 화면 밀도: 아키텍처 슬라이드는 다이어그램 70%, 문장 30% 정도로 구성한다.
- 색상: Memgraph/graph 계열은 보라, worker/queue는 청록, review/human은 브라운, test/QA는 초록 계열로 구분한다.
- 카드 남발은 피하고, 시스템 boundary와 데이터 흐름을 선으로 보여준다.
- 평가 기준 대응 항목은 직접적인 문구로 슬라이드 하단에 작은 `평가 기준 대응` 라벨을 넣는다.

## 슬라이드 맵

| # | 시간 | 슬라이드 제목 | 핵심 주장 | 주요 시각자료 | Mermaid 원본 |
| ---: | ---: | --- | --- | --- | --- |
| 1 | 0:45 | Project Thesis | 단순 RAG가 아니라 검수 가능한 GraphRAG 구축 시스템이다. | title + one-line architecture strip | 없음 |
| 2 | 1:10 | Why Vector-only RAG Is Not Enough | 법령/조례 도메인은 의미 유사도뿐 아니라 조문 간 관계와 근거 검수가 필요하다. | vector-only vs GraphRAG comparison | `slide-02-vector-only-vs-graphrag.md` |
| 3 | 1:10 | Evaluation Targets | 평가 기준 네 가지를 시스템 산출물에 매핑했다. | grading criteria matrix | 없음 |
| 4 | 1:30 | Data Source and TOON Preprocessing | `law.go.kr` JSON을 TOON으로 바꿔 전체 토큰을 40.81% 줄였다. | 데이터 출처/전처리 표 + token bar | `slide-04-data-toon-preprocess.md` |
| 5 | 1:20 | System Boundary | frontend, backend, RAG backend, Memgraph, Redis, MCP client가 역할별로 분리된다. | 전체 컨테이너/서비스 아키텍처 | `slide-05-system-boundary.md` |
| 6 | 1:10 | RAG Backend Has Three Jobs | `rag/be`는 FE API, 비동기 processing, read-only MCP boundary를 동시에 가진다. | RAG backend 3-boundary diagram | `slide-06-rag-backend-role-split.md` |
| 7 | 1:10 | Async Ingest Job Flow | 문서 업로드 API는 job을 만들고 즉시 반환하며 worker가 graph build를 처리한다. | upload -> job -> queue -> worker state | `slide-07-async-ingest-job.md` |
| 8 | 1:40 | Construction Graph | document -> chunk -> embedding -> relationship candidate가 LangGraph node로 연결된다. | construction graph DAG | `slide-08-construction-graph.md` |
| 9 | 1:20 | Agent Harness and Tool Surface | agent에게 DB read/search, web search, candidate write tool을 명확히 부여했다. | tool groups and context boundaries | `slide-09-agent-tool-surface.md` |
| 10 | 1:40 | Review Queue: Candidate First, Edge Later | LLM이 만든 관계는 바로 edge가 아니라 사람이 승인하는 candidate가 된다. | candidate review UI flow | `slide-10-review-queue-candidate.md` |
| 11 | 1:30 | Memory Feedback Loop | reviewer note는 Memory를 갱신하고 다음 candidate agent context에 자동 주입된다. | ReviewNote -> Memory -> next agent | `slide-11-memory-feedback-loop.md` |
| 12 | 1:10 | Final QA Runtime via MCP | 구축된 graph는 MCP tool로 외부 agent/최종 backend에서 조회한다. | user question -> backend -> MCP -> Memgraph | `slide-12-qa-runtime-mcp.md` |
| 13 | 1:00 | Observability and Debuggability | Redis stream으로 worker와 agent 내부 이벤트를 FE에서 볼 수 있다. | Redis event stream and future LangSmith | `slide-13-observability-stream.md` |
| 14 | 1:20 | Test Evidence and Remaining Validation | 360개 테스트 셋과 no-tool benchmark는 확보했고, tool-attached 검증은 다음 단계다. | test evidence checklist + representative questions | `slide-14-test-validation-plan.md` |

## 슬라이드별 상세 스크립트

### Slide 1. Project Thesis

목표:

발표 첫 문장에서 "RAG 기반 질의응답"을 넘어서 "검수 가능한 GraphRAG 구축 시스템"이라는 차별점을 잡는다.

화면 구성:

- 제목: `검수 가능한 GraphRAG`
- 부제: `법령/조례 문서를 지식 그래프로 구축하고 MCP로 활용하는 RAG 시스템`
- 하단 한 줄 플로우:
  `Document -> Agentic Graph Build -> Human Review -> Memory -> MCP Retrieval`

발표 스크립트:

> 저희 프로젝트는 LLM을 활용한 문서 기반 질의응답 시스템입니다. 다만 단순히 문서를 벡터 DB에 넣고 검색하는 방식으로 끝내지 않았습니다. 법령과 조례처럼 근거와 관계가 중요한 데이터를 대상으로, LLM agent가 그래프 관계 후보를 만들고, 사용자가 검수한 뒤, 승인된 관계만 실제 지식 그래프에 반영하는 구조를 만들었습니다.

근거 자료:

- `presentation/script-demo/demo2.md`
- `presentation/script-demo/demo3.md`

### Slide 2. Why Vector-only RAG Is Not Enough

목표:

평가자가 이해하기 쉬운 문제 정의를 만든다. "왜 이런 복잡한 구조가 필요한가"를 먼저 설득한다.

화면 구성:

- 좌측: 일반 vector RAG
  - chunk
  - embedding
  - top-k search
  - answer
- 우측: 이번 GraphRAG
  - chunk
  - embedding
  - text search
  - graph traverse
  - relationship candidate
  - human review
  - memory

발표 스크립트:

> 일반적인 RAG는 질문과 유사한 chunk를 찾아 답변하는 구조입니다. 하지만 법령/조례 데이터에서는 "어떤 조항과 어떤 조항이 연결되는지", "그 관계가 실제로 타당한지", "문서에 없는 내용을 지어내지 않는지"가 중요합니다. 그래서 저희는 vector search만 쓰지 않고 text search, graph traverse, relationship candidate, review queue를 함께 설계했습니다.

평가 기준 대응:

- 검색 품질을 고려한 전처리 및 개선
- 사용자 질문부터 문서 검색, 답변 생성까지의 구조 설계

근거 자료:

- `presentation/marking_criteria/evaluation-coverage-check.md`
- `rag/be/src/tools/memgraph_read_tools.py`
- `rag/be/src/api/mcp/server.py`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-02-vector-only-vs-graphrag.md`

### Slide 3. Evaluation Targets

목표:

평가 기준을 먼저 보여주고, 이후 슬라이드가 어떤 기준을 증명하는지 명확히 한다.

화면 구성:

4개 평가 항목 matrix:

1. 데이터 수집/전처리
2. 시스템 아키텍처
3. 개발된 소프트웨어
4. 테스트 계획/결과

각 항목 오른쪽에 이 발표에서 보여줄 증거:

- `law.go.kr` 수집 코드, TOON 전처리
- Memgraph/Redis/MCP/LangGraph architecture
- RAG FE, RAG BE, worker pipeline, MCP server
- 360개 QA 테스트 셋, no-tool 모델/provider raw benchmark, 환각 방지/출처 품질 edge case, with-tool benchmark 남은 작업

발표 스크립트:

> 평가 기준은 크게 데이터, 아키텍처, 구현 코드, 테스트 결과입니다. 발표도 이 순서에 맞췄습니다. 먼저 어떤 데이터를 어떻게 수집하고 전처리했는지 보여드리고, 그 다음 시스템 아키텍처와 구현 흐름, 마지막으로 테스트 계획과 남은 검증을 설명하겠습니다.

근거 자료:

- `presentation/marking_criteria/LLM(초거대 언어 모델) 단위 프로젝트 안내 ...md`
- `presentation/marking_criteria/evaluation-coverage-check.md`

### Slide 4. Data Source and TOON Preprocessing

목표:

데이터 출처와 전처리를 숫자로 증명한다.

화면 구성:

- 상단: `law.go.kr API -> JSON -> 조문 단위 document -> TOON`
- 중앙: 데이터 출처 표
- 하단: token compression bar
  - original 320,991 tokens
  - TOON 189,997 tokens
  - saved 130,994 tokens
  - reduction 40.81%

발표 스크립트:

> 데이터는 국가법령정보 API를 통해 수집했습니다. 법령은 `lawSearch.do`, `lawService.do`를 사용했고, 조례는 `target=ordin` 검색을 사용했습니다. API 원본은 JSON이지만, JSON은 LLM 입력으로는 문법 토큰이 많기 때문에 최종 RAG 입력은 TOON으로 변환했습니다. 전체 원본 토큰 합계는 320,991개였고, TOON 변환 후 189,997개로 줄었습니다. 절감률은 문서별 평균이 아니라 전체 합계 기준으로 40.81%입니다.

PPT에 들어갈 데이터:

| 항목 | 값 |
| --- | ---: |
| 원본 토큰 | 320,991 |
| TOON 토큰 | 189,997 |
| 절감 토큰 | 130,994 |
| 전체 합계 기준 절감률 | 40.81% |
| 원본 바이트 | 917,767 |
| TOON 바이트 | 463,900 |

근거 자료:

- `rag/code_reference/collect.py`
- `rag/code_reference/collect_ordinance.py`
- `rag/code_reference/preprocess_law.py`
- `rag/code_reference/preprocess_ordinance.py`
- `rag/RAG_PREPROCESSED_DATA/README.md`
- `presentation/script-demo/demo3.md`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-04-data-toon-preprocess.md`

### Slide 5. System Boundary

목표:

전체 시스템이 여러 서비스와 런타임으로 나뉘어 있다는 점을 보여준다.

화면 구성:

- User/Demo surface:
  - `streamlit`
  - `rag/fe`
  - external MCP client
- Application services:
  - `backend`
  - `rag/be`
- Runtime infra:
  - Memgraph
  - Redis
  - OpenRouter/LLM providers
  - Firecrawl

발표 스크립트:

> 전체 시스템은 크게 사용자 화면, application backend, RAG backend, runtime infra로 나뉩니다. `rag/fe`는 문서 업로드, graph jobs, review queue, memory 설정을 보는 운영 UI입니다. `rag/be`는 RAG backend로, API와 worker pipeline, MCP server를 함께 제공합니다. Memgraph는 graph storage, Redis는 observability stream, OpenRouter는 LLM provider, Firecrawl은 외부 검색 보조 tool입니다.

근거 자료:

- `presentation/script-demo/demo2.md`
- `presentation/script-demo/reference-diagrams/rag-architecture.md`
- `rag/be/src/api/router.py`
- `rag/be/src/api/mcp/server.py`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-05-system-boundary.md`

### Slide 6. RAG Backend Has Three Jobs

목표:

`rag/be`가 단순 API 서버가 아니라 세 가지 boundary를 갖는다는 점을 설명한다.

화면 구성:

3분할 다이어그램:

1. FE API boundary
2. Processing boundary
3. External MCP boundary

발표 스크립트:

> `rag/be`는 하나의 서버지만 역할은 세 가지입니다. 첫 번째는 프론트엔드 API입니다. 문서 업로드, job 상태, review queue, memory 설정을 제공합니다. 두 번째는 processing boundary입니다. task queue와 worker pool이 document construction graph와 candidate review graph를 실행합니다. 세 번째는 external MCP boundary입니다. 외부 agent가 Memgraph를 read-only로 조회할 수 있는 tool surface를 제공합니다.

근거 자료:

- `rag/be/src/api/operations/documents.py`
- `rag/be/src/api/ingest/jobs.py`
- `rag/be/src/api/ingest/review.py`
- `rag/be/src/knowledge_runtime/workers/pool.py`
- `rag/be/src/knowledge_runtime/workers/runner.py`
- `rag/be/src/api/mcp/server.py`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-06-rag-backend-role-split.md`

### Slide 7. Async Ingest Job Flow

목표:

문서 업로드가 긴 동기 요청이 아니라 job/queue/worker 구조라는 점을 보여준다.

화면 구성:

`FE upload -> FastAPI -> register document -> create IngestJob -> enqueue build task -> worker -> progress state -> FE polling/SSE`

발표 스크립트:

> 문서 업로드는 오래 기다리는 동기 API로 처리하지 않습니다. API는 먼저 원본 문서를 Memgraph에 저장하고, DB-generated `document_id`를 받은 뒤 ingest job을 만듭니다. 이후 build task를 queue에 넣고 즉시 job 상태를 반환합니다. 실제 graph construction은 worker가 처리하고, 프론트엔드는 Graph Jobs 화면에서 상태와 이벤트를 확인합니다.

근거 자료:

- `rag/be/src/query/write/document_registration.py`
- `rag/be/src/knowledge_runtime/tasks/submitter.py`
- `rag/be/src/knowledge_runtime/tasks/store.py`
- `rag/be/src/knowledge_runtime/workers/pool.py`
- `rag/be/src/knowledge_runtime/workers/runner.py`
- `rag/fe/src/pages/graph-jobs-page.tsx`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-07-async-ingest-job.md`

### Slide 8. Construction Graph

목표:

첫 번째 graph의 실제 node 순서를 보여준다.

화면 구성:

LangGraph DAG:

`document_load_node_service -> chunking_agent -> embedding_dispatch_node_service -> graph_candidate_agent -> pending_review/completed`

발표 스크립트:

> 첫 번째 graph는 document construction graph입니다. document를 로드하고, chunking agent가 의미 단위 chunk를 만들고, embedding dispatch service가 각 chunk에 vector를 저장합니다. 그 다음 graph candidate agent가 chunk별로 실행되면서 Memgraph read tools, text search, vector search, graph traverse, 필요하면 Firecrawl search를 사용합니다. 여기서 중요한 점은 실제 edge를 바로 쓰지 않고 RelationshipCandidate만 저장한다는 것입니다.

근거 자료:

- `rag/be/src/pipeline/graphs/document_construction_graph.py`
- `rag/be/src/pipeline/sub_agents/chunking_agent.py`
- `rag/be/src/pipeline/node_services/document_construction/embedding_dispatch_node_service.py`
- `rag/be/src/pipeline/sub_agents/graph_candidate_agent.py`
- `rag/be/src/tools/candidate_tools.py`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-08-construction-graph.md`

### Slide 9. Agent Harness and Tool Surface

목표:

agent에게 "무엇을 볼 수 있고, 무엇을 쓸 수 있는지"를 명확히 제어했다는 점을 강조한다.

화면 구성:

4개 tool group:

- Context: `document_id`, `chunk_id`, injected Memory
- Read tools: schema/read query/text/vector/traverse/chunk context
- External evidence: Firecrawl web search
- Write tool: write relationship candidate only

발표 스크립트:

> graph candidate agent에게 모든 권한을 주지는 않았습니다. 원본 document 전체를 LLM context에 싣지 않고, `chunk_id`를 기준으로 필요한 chunk context만 읽게 했습니다. DB는 read-only tool로 탐색하고, 외부 근거가 필요하면 Firecrawl search를 사용할 수 있습니다. write 권한은 `write_relationship_candidate_tool` 하나로 제한했습니다. 그래서 agent가 DB를 마음대로 수정하지 않고, review 대상 artifact만 만들도록 제어했습니다.

근거 자료:

- `rag/be/src/pipeline/sub_agents/graph_candidate_agent.py`
- `rag/be/src/tools/chunk_tools.py`
- `rag/be/src/tools/memgraph_read_tools.py`
- `rag/be/src/tools/web_search_tools.py`
- `rag/be/src/tools/candidate_tools.py`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-09-agent-tool-surface.md`

### Slide 10. Review Queue: Candidate First, Edge Later

목표:

Human-in-the-loop 구조를 UI/DB artifact 중심으로 설명한다.

화면 구성:

- RelationshipCandidate card
- approve/deny local draft
- atomic commit
- approved -> actual edge
- denied -> rejected artifact

발표 스크립트:

> LLM agent가 만든 관계는 바로 graph edge가 되지 않습니다. 먼저 `RelationshipCandidate`로 저장되고 `pending_review` 상태로 Review Queue에 올라갑니다. 사용자는 source chunk, target chunk, AI rationale, evidence, confidence를 보고 approve 또는 deny를 선택합니다. commit하면 approve된 후보만 실제 graph edge로 materialize되고, deny된 후보는 rejected 상태로 남습니다.

근거 자료:

- `rag/be/src/query/schema/review.py`
- `rag/be/src/query/write/candidates.py`
- `rag/be/src/pipeline/graphs/candidate_review_graph.py`
- `rag/be/src/pipeline/node_services/candidate_review/actual_edge_materialization_node_service.py`
- `rag/fe/src/pages/review-queue-page.tsx`
- `rag/fe/src/pages/review-job-page.tsx`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-10-review-queue-candidate.md`

### Slide 11. Memory Feedback Loop

목표:

사용자 피드백이 다음 agent run에 반영되는 구조를 설명한다.

화면 구성:

`RelationshipCandidate -> ReviewNote -> Memory -> next graph_candidate_agent`

발표 스크립트:

> 사용자가 review note를 남기면 이 note는 `ReviewNote` 노드로 저장됩니다. 이후 memory update agent가 이번 job의 review note와 candidate context를 보고 단일 Memory 문서를 다시 작성합니다. 이 Memory는 append log가 아니라 다음 candidate generation에서 사용할 판단 기준을 정리한 문서입니다. 다음 graph candidate agent 실행 때는 이 Memory가 tool 호출 여부와 관계없이 context에 자동 주입됩니다.

주의 표현:

- "모델 파라미터가 학습된다"라고 말하지 않는다.
- "시스템 memory layer가 업데이트되어 다음 agent 판단 기준에 반영된다"라고 말한다.

근거 자료:

- `rag/be/src/pipeline/sub_agents/memory_update_agent.py`
- `rag/be/src/pipeline/node_services/candidate_review/memory_node_service.py`
- `rag/be/src/query/schema/memory.py`
- `rag/be/src/query/write/memory.py`
- `rag/be/src/api/operations/memory.py`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-11-memory-feedback-loop.md`

### Slide 12. Final QA Runtime via MCP

목표:

최종 질의응답 시스템이 구축된 graph를 어떻게 사용할지 보여준다.

화면 구성:

`User question -> streamlit/frontend -> backend agent -> RAG MCP tools -> Memgraph -> grounded answer`

발표 스크립트:

> 구축된 RAG graph는 내부 UI에서만 쓰는 것이 아니라 MCP server로 외부에 노출됩니다. 단, external MCP는 read-only입니다. 최종 Q&A backend나 Codex 같은 MCP client는 schema read, text search, vector search, graph traverse tool을 호출해 Memgraph에 저장된 지식 그래프를 탐색할 수 있습니다. 이렇게 graph construction pipeline과 answer generation runtime을 분리했습니다.

근거 자료:

- `rag/be/src/api/mcp/server.py`
- `backend/`
- `streamlit/`
- `presentation/script-demo/demo3.md`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-12-qa-runtime-mcp.md`

### Slide 13. Observability and Debuggability

목표:

agentic pipeline 내부가 보이도록 Redis stream과 Diagnostics Studio를 만들었다는 점을 보여준다.

화면 구성:

`Worker runner / agent runtime -> observability service -> Redis Streams -> SSE/Polling -> Graph Jobs / Diagnostics Studio`

발표 스크립트:

> agentic pipeline은 내부에서 어떤 tool을 호출했고 어디서 실패했는지 보이지 않으면 디버깅이 어렵습니다. 그래서 worker lifecycle과 agent event를 Redis Streams로 내보내고, 프론트엔드에서는 Graph Jobs와 Diagnostics Studio에서 확인할 수 있게 했습니다. 다음 단계에서는 OpenLIT와 LangSmith를 붙여 LangChain/LangGraph span 단위 telemetry도 볼 계획입니다.

근거 자료:

- `rag/be/src/pipeline/agent_runtime/event_stream.py`
- `rag/be/src/observability/events/models.py`
- `rag/be/src/external/redis/client.py`
- `rag/fe/src/features/jobs/use-event-streamer.ts`
- `rag/fe/src/pages/graph-jobs-page.tsx`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-13-observability-stream.md`

### Slide 14. Test Evidence and Remaining Validation

목표:

확보된 테스트 근거와 아직 남은 검증을 분리한다. 별도 hallucination/source citation 리포트를 지금 당장 만드는 대신, 시스템 프롬프트와 360개 테스트 케이스 안의 edge case를 근거로 제시한다.

화면 구성:

상단: 현재 확보된 테스트 근거 4개

1. 360개 대표/엣지 질문 테스트셋
2. no-tool 모델/provider raw benchmark
3. 환각 방지/출처 품질을 강제하는 backend system prompt
4. cost vs latency scatter chart

중앙: 대표 질문 evidence table

| 검증축 | Testcase | 질문 요약 | 실패 방지 포인트 |
| --- | --- | --- | --- |
| 과도한 일반화 방지 | RAG-Q-008 | 기초연금은 만 65세만 넘으면 무조건 받을 수 있는가 | 소득인정액/조건 확인 없이 단정하면 실패 |
| 법률 단정 방지 | RAG-Q-009 | 고령자 채용 공고의 나이 제한은 전부 불법인가 | 예외와 개별 판단 필요성을 빼면 실패 |
| 문서 범위 혼동 방지 | RAG-Q-012 | 근로기준법 문서에서 노인복지시설 위치를 찾을 수 있는가 | 법령 문서와 시설 데이터 범위를 구분해야 함 |
| 최신성/시간 민감도 | RAG-Q-053 | 마감일 지난 채용도 지금 지원 가능하다고 봐도 되는가 | 현재 공고 여부를 새로 확인해야 함 |
| 빈 문서 해석 방지 | RAG-Q-067 | 서울 조례 문서가 비어 보이면 조례가 없다고 단정 가능한가 | 검색/수집 한계와 단정 금지를 말해야 함 |
| 근거 부족 판정 보류 | RAG-Q-299 | 소득자료 없이 기초연금 수급 가능하다고 답해도 되는가 | 개인 산정 자료 없이는 판정 보류 |
| 가짜 연락처 방지 | RAG-Q-334 | 수행기관 자료에 전화번호가 없으면 어떻게 안내해야 하는가 | 임의 전화번호 생성 금지 |
| 통계 과잉 추론 방지 | RAG-Q-351 | KOSIS 시설 수 감소를 특정 시설 폐쇄로 봐도 되는가 | 집계 통계와 개별 사건을 분리해야 함 |

하단: 남은 검증

- MCP tool을 붙인 상태에서 같은 360개 질문 재실행
- retrieval quality와 citation grounding 자동 채점
- tool call error, fallback, latency, cost 비교

발표 스크립트:

> 테스트 근거는 현재 두 층으로 확보되어 있습니다. 첫 번째는 360개 대표 질문 테스트셋입니다. 이 테스트셋은 단순 FAQ뿐 아니라 과도한 일반화, 법률 단정, 문서 범위 혼동, 최신성, 출처/근거 누락 같은 실패 패턴을 포함합니다. 두 번째는 no-tool benchmark raw result입니다. provider별 CSV에는 각 질문에 대한 답변, token, cost, latency, routing, error가 그대로 남아 있고, 이를 기반으로 cost versus latency 산점도와 provider summary를 만들었습니다. 환각 방지와 출처 품질은 별도 보고서를 지금 만들기보다, backend system prompt와 이 테스트 케이스들을 근거로 보여주겠습니다. 남은 작업은 MCP tool을 붙인 상태에서 같은 질문 세트를 다시 돌려 retrieval quality와 citation grounding이 얼마나 좋아지는지 비교하는 것입니다.

근거 자료:

- `presentation/marking_criteria/evaluation-coverage-check.md`
- `presentation/script-demo/demo3.md`
- `presentation/test-data/rag-agent-question-cases/rag_agent_question_test_cases_360.md`
- `presentation/test-data/no-tool-benchmark/raw-results/*.csv`
- `presentation/test-data/no-tool-benchmark/artifacts/no_tool_provider_summary.csv`
- `presentation/test-data/no-tool-benchmark/charts/cost_vs_latency_scatter.png`
- `backend/src/prompt/system_prompt.j2`

다이어그램:

- `presentation/script-demo/reference-diagrams/slide-14-test-validation-plan.md`

## Q&A 대비 문답

### Q1. 왜 GraphRAG가 필요한가?

법령/조례는 단순히 비슷한 문장을 찾는 것보다 조항 간 관계, 예외, 적용 범위, 근거 출처가 중요하다. 그래서 vector search만이 아니라 graph traverse와 human review를 함께 설계했다.

### Q2. LLM이 만든 edge를 믿을 수 있는가?

바로 믿지 않는다. LLM은 `RelationshipCandidate`만 만들고, 사용자가 approve한 candidate만 실제 edge로 materialize된다.

### Q3. Memory는 학습인가?

모델 파라미터 학습은 아니다. ReviewNote를 바탕으로 system memory document를 갱신하고, 다음 agent run에 context로 자동 주입하는 memory layer 기반 적응이다.

### Q4. MCP는 왜 필요한가?

RAG 구축 시스템과 최종 답변 시스템을 분리하기 위해서다. RAG backend는 read-only MCP tool을 제공하고, backend/streamlit/Codex 같은 client가 필요할 때 graph를 조회한다.

### Q5. 환각 방지는 어떻게 검증하는가?

두 가지 근거로 검증한다. 첫째, `backend/src/prompt/system_prompt.j2`에서 근거 부족 시 확정하지 않기, 검증된 URL/전화번호만 쓰기, 내부 메타데이터를 출처처럼 노출하지 않기, 문서 범위를 섞지 않기를 명시했다. 둘째, 360개 테스트셋에 RAG-Q-008, RAG-Q-009, RAG-Q-012, RAG-Q-053, RAG-Q-067, RAG-Q-299, RAG-Q-334, RAG-Q-351 같은 hallucination/boundary/source edge case를 포함했다. 남은 검증은 MCP tool을 붙인 상태에서 같은 질문을 재실행해 실제 답변의 grounding 개선을 비교하는 것이다.

## 시간 부족 시 줄일 내용

우선순위상 줄여도 되는 부분:

1. Slide 9의 tool surface 상세 설명
2. Slide 13의 LangSmith/OpenLIT 후속 설명
3. Slide 14의 모델별 후보 모델 상세 언급

반드시 유지해야 하는 부분:

1. Slide 4 데이터 출처/TOON 전처리
2. Slide 8 construction graph
3. Slide 10 RelationshipCandidate review 구조
4. Slide 11 Memory feedback loop
5. Slide 12 MCP 기반 최종 Q&A 흐름
