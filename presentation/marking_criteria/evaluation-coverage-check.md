# Evaluation Coverage Check

기준 문서: `presentation/marking_criteria/LLM(...) 단위 프로젝트 안내 ...md`

목적: 발표/시연에서 평가 기준을 빠뜨리지 않도록 현재 준비된 내용과 보강할 내용을 매핑한다.

## 총평

현재 RAG 시스템은 평가 기준의 기술 구현 항목은 강하게 만족한다.
특히 단순 vector RAG가 아니라 Memgraph 기반 GraphRAG, async ingest pipeline,
human-in-the-loop review, Memory feedback loop, read-only MCP exposure까지 구현되어
있어서 "시스템 아키텍처"와 "개발된 소프트웨어" 항목은 차별점이 충분하다.

다만 발표/보고서 관점에서는 아래 증거가 아직 명시적으로 부족하다.

- 수집 데이터의 출처/형식/전처리 과정을 표로 정리한 근거.
- 대표 질문 테스트셋과 모델별 성능 비교 결과.
- 문서에 없는 질문에 대한 환각 방지 테스트.
- 검색 결과와 답변이 어떤 근거 chunk/source를 참조했는지의 정량/정성 평가.
- 최종 사용자 질의응답 runtime(`streamlit -> backend -> RAG MCP -> Memgraph`) 흐름 설명.

## 평가 기준별 커버리지

| 평가 항목 | 현재 커버리지 | 보강 필요 |
| --- | --- | --- |
| 수집 데이터 및 데이터 전처리 문서 | 법률/조례 데이터 기반 GraphRAG ingest 구조가 있고, `RAG_ORIGINAL_DATA`, `RAG_PREPROCESSED_DATA`, `.toon`, raw/cleaned sample 산출물이 있다. Chunk에는 `chunk_name`, `chunk_description`, `summary`, `document_id`, embedding metadata가 들어간다. | 데이터 출처, 수집 방식, 원본 형식, 전처리 결과 파일 수, 문서 수, chunk 수를 표로 정리해야 한다. 발표에서는 "국가법령/조례 데이터 -> toon/json/cleaned text -> Document/Chunk" 흐름을 보여줘야 한다. |
| 문서 정제, 분할, 메타데이터 구성 | `chunking_agent`가 사람이 읽을 수 있는 chunk name/description을 만들고, DB-generated document/chunk id를 사용한다. Review UI에서도 chunk title/description을 보여준다. | 청킹 기준을 명시해야 한다. 예: 의미 단위, 너무 긴 chunk 제한, 원문 boundary, chunk name/description 생성 이유. 전처리 전/후 예시 1개가 필요하다. |
| 검색 품질을 고려한 개선 | vector search뿐 아니라 text search, graph traverse, read query, Firecrawl search까지 agent tool로 제공한다. | "왜 단순 vector search만으로 부족했는지"와 "GraphRAG/Memgraph로 개선한 점"을 짧은 before/after로 보여줘야 한다. |
| 시스템 아키텍처 | `demo2.md`와 `reference-diagrams/rag-architecture.md`에 RAG backend, task queue, worker, Memgraph, Redis, MCP boundary가 정리되어 있다. | 최종 질의응답 runtime인 `streamlit -> backend -> RAG MCP -> Memgraph -> backend answer` 다이어그램을 추가해야 한다. 지금 다이어그램은 RAG 구축/운영 쪽이 더 강하다. |
| LLM, embedding, vector DB, LangChain 역할 구분 | LLM sub-agent, embedding dispatch, Memgraph storage/search, LangChain/LangGraph orchestration이 코드와 문서에 분리되어 있다. | 발표 슬라이드에 역할 분담 표가 필요하다. 예: LLM은 chunk/candidate/reasoning, embedding은 semantic search, Memgraph는 graph/vector/text store, LangChain/LangGraph는 agent orchestration. |
| RAG 질의응답 전체 구조 | RAG 구축 pipeline과 MCP exposure는 설명되어 있다. | 사용자가 질문했을 때 실제 answer가 어떻게 RAG MCP tool을 통해 근거를 가져오는지는 별도 슬라이드가 필요하다. backend 쪽 MCP consumer 연결이 최종 범위라면 그 상태를 명확히 말해야 한다. |
| 구현 범위와 주요 기술 요소 | FastAPI, FastMCP, Memgraph, Redis, OpenRouter, Firecrawl, LangChain/LangGraph, React RAG Ops UI가 있다. | "이번 3차 프로젝트 범위"와 "추후 4차/운영 범위"를 분리해야 한다. 예: ASR/음성, 장기 세션 저장, durable queue, LangSmith telemetry는 후속 범위. |
| 문서 임베딩, 벡터 DB 저장, 유사도 검색 | Chunk embedding update가 있고 Memgraph vector search tool을 MCP/internal tool surface에서 제공한다. | live demo나 smoke result로 `Chunk.embedding_status`, vector index/search 결과를 보여주는 쿼리 또는 화면이 필요하다. |
| LangChain 기반 검색 결과 + LLM 답변 파이프라인 | RAG 구축 agent pipeline은 LangChain/LangGraph로 구현됨. MCP read tools도 준비됨. | 채점 기준은 "질의응답"을 직접 본다. 최종 backend agent가 MCP RAG tools를 실제로 붙여 답변하는 demo가 필요하다. 아직 placeholder라면 발표에서 "RAG 구축/노출 완료, backend consumer 연결 단계"라고 정확히 말해야 한다. |
| 근거 기반 프롬프트 구성 | graph_candidate_agent와 memory_update_agent는 근거, candidate, memory context를 명확히 사용한다. | 최종 Q&A agent prompt에서 "근거 chunk/source를 포함해 답변하라"가 들어가야 한다. 답변 예시에 source/citation 형태가 보여야 한다. |
| 코드 구조와 실행 가능성 | `rag/be`, `rag/fe`, `backend`, `streamlit`이 서비스별로 분리되어 있고 커밋 완료됨. | README에 "demo 실행 순서"를 한 장으로 정리해야 한다. Docker/Memgraph/Redis/RAG backend/RAG FE/backend/streamlit 순서가 필요하다. |
| 대표 질문 테스트 | 원격에 모델별 테스트 데이터가 있다고 했으나 현재 local에는 아직 없음. | remote merge 후 모델별 대표 질문 테스트 결과 표가 반드시 필요하다. 최소: 질문 수, 모델명, context length, 평균 latency, 평균 input/output token, 비용, 정답률/근거 충실도. |
| 문서에 없는 질문 환각 방지 | 설계상 MCP/RAG 근거 기반 답변, candidate review, Memory context가 있지만 최종 Q&A hallucination test 결과는 아직 없음. | out-of-corpus 질문 테스트를 추가해야 한다. 예: "문서에 근거가 없으면 모른다고 답하는가", "가짜 법 조항을 만들어내지 않는가". |
| 검색 결과와 답변 정확성/근거 포함 | Review Queue에서는 candidate rationale/evidence를 검토할 수 있다. 하지만 최종 Q&A 평가와는 별도다. | 최종 답변마다 retrieved chunk ids/document titles/source snippets를 기록하고, human judge가 근거 적합성을 평가한 표가 필요하다. |
| 테스트 결과와 개선 사항 보고 | 일부 unit/integration test와 live smoke는 있음. 모델 비교 결과는 remote 데이터 merge 이후 작성 예정. | `테스트 계획 및 결과 보고서`를 별도 markdown으로 만들어야 한다. "실패 사례 -> 개선 조치"를 넣어야 점수 대응이 좋다. |

## 추가해야 할 발표/보고서 항목

### 1. 데이터셋 요약 표

필수 컬럼:

- 데이터 출처
- 문서 종류
- 원본 형식
- 전처리 형식
- 문서 수
- chunk 수
- 사용 목적

예시:

| 출처 | 문서 종류 | 원본 형식 | 전처리 형식 | 문서 수 | chunk 수 | 사용 목적 |
| --- | --- | --- | --- | ---: | ---: | --- |
| 국가법령/조례 데이터 | 법령, 조례 | json/toon/text | cleaned markdown/text | TBD | TBD | 법률 RAG grounding |

### 2. 모델 평가 표

remote 테스트 데이터 merge 후 작성할 것.

필수 컬럼:

- 모델명
- provider
- context length
- 평균 latency
- 평균 input token
- 평균 output token
- 예상 비용
- 정답률 또는 human score
- 근거 포함률
- tool call 성공률
- 주요 실패 유형

### 3. RAG 성능 평가 축

모델 자체 성능만 보면 부족하다. RAG 시스템이므로 아래 축을 같이 봐야 한다.

- Retrieval relevance: 질문과 검색된 chunk가 실제로 관련 있는가.
- Groundedness: 답변이 검색된 근거 안에서만 생성되는가.
- Citation/source quality: 답변에 문서명/chunk/source가 붙는가.
- Refusal behavior: 문서에 없는 질문에 모른다고 답하는가.
- Tool-use reliability: MCP tool call 실패율, 잘못된 tool 호출률.
- Latency/cost: 사용자 질문 1건당 시간과 비용.
- Graph usefulness: vector-only보다 graph traverse가 더 나은 사례가 있는가.

### 4. GraphRAG 구축 평가 축

우리 시스템의 차별점이므로 별도로 보여주는 게 좋다.

- Chunk quality: chunk name/description이 사람이 읽을 수 있는가.
- Candidate quality: RelationshipCandidate가 실제 관계 후보로 의미 있는가.
- Review efficiency: 사용자가 candidate를 빠르게 판단할 수 있는가.
- Approved edge precision: approve된 edge 중 실제로 타당한 비율.
- Memory effect: reviewer note 이후 다음 candidate generation에서 사용자 기준이 반영되는가.

### 5. 최종 데모 체크리스트

1. 문서 업로드.
2. Graph Jobs에서 async task 진행 확인.
3. Diagnostics Studio에서 agent/tool event 확인.
4. Review Queue에서 RelationshipCandidate 확인.
5. approve/deny와 reviewer note 입력.
6. Memgraph에서 `RelationshipCandidate -> ReviewNote -> Memory` 확인.
7. MCP read-only tool로 graph 조회.
8. backend/streamlit에서 실제 질문 답변이 RAG 근거를 사용하는지 확인.

## 현재 가장 큰 리스크

1. 최종 Q&A backend가 아직 RAG MCP tool을 실제로 소비하는 demo가 부족하면, 평가자가 "RAG 기반 질의응답" 완성도를 낮게 볼 수 있다.
2. 모델별 테스트 데이터가 remote에만 있고 아직 보고서에 반영되지 않았으므로, "테스트 계획 및 결과 보고서" 항목이 약하다.
3. 문서에 없는 질문에 대한 hallucination 방지 검증이 없으면 프로젝트 목표의 첫 문장인 "환각 방지"를 증명하기 어렵다.
4. 데이터 출처/전처리 과정이 구술로만 설명되면 산출물 점수에서 손해가 난다.

## 결론

지금 구현물의 차별점은 충분하다. 다만 채점 기준 대응을 위해서는 발표 전에 다음 문서를 추가하는 것이 좋다.

- `dataset-summary.md`: 데이터 출처, 전처리, chunk 통계.
- `model-evaluation-report.md`: 모델별 테스트 결과.
- `rag-qa-test-report.md`: 대표 질문, 문서 외 질문, 근거 포함 여부.
- `demo-runbook.md`: 실행 순서와 live demo query.

