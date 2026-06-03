# Demo 2. RAG 시스템 아키텍처 설명 스크립트

## 이 파트에서 전달할 핵심

이번 RAG 시스템의 핵심은 단순히 문서를 벡터 DB에 넣고 검색하는 것이 아니다.
문서를 Memgraph 기반 knowledge graph로 편입하되, LLM agent가 만든 관계를 바로
실제 edge로 확정하지 않고 `RelationshipCandidate`라는 검토 대상 artifact로 먼저
저장한다. 이후 사용자가 Review Queue에서 approve/deny를 결정하면 그때 실제 edge가
생성되거나 candidate 상태가 reject로 확정된다.

이 구조 덕분에 시스템은 자동화된 graph construction과 human-in-the-loop review를
동시에 가진다. agent는 그래프를 빠르게 확장하고, 사용자는 중요한 관계만 승인하면서
품질을 통제한다.

## 발표 스크립트

이제 RAG 파이프라인을 아키텍처 관점에서 설명하겠습니다.

일반적인 RAG 시스템은 문서를 청크로 나누고, 청크를 임베딩해서, 질문이 들어왔을 때
유사한 청크를 찾는 방식으로 끝나는 경우가 많습니다. 저희 시스템은 여기서 한 단계 더
나아가서, 청크와 청크 사이의 관계를 그래프 형태로 구축합니다. 다만 이 관계를 LLM이
제안했다고 해서 바로 데이터베이스의 최종 edge로 저장하지는 않습니다.

대신 LLM agent가 찾은 관계는 먼저 `RelationshipCandidate`로 저장됩니다. 이 candidate는
source chunk, target chunk, 관계 타입, 근거 문장, agent의 rationale, confidence metadata를
가지고 있고, 상태는 처음에 `pending_review`입니다. 즉 agent가 "이 두 청크는 관련 있어
보입니다"라고 제안하면, 시스템은 그것을 최종 지식으로 확정하지 않고 review queue에
올립니다.

프론트엔드에서는 사용자가 이 candidate를 보고 approve 또는 deny를 선택할 수 있습니다.
approve가 되면 해당 candidate를 바탕으로 실제 graph edge가 materialize되고, deny가 되면
candidate는 rejected 상태로 남습니다. 이 방식은 LLM hallucination을 줄이기 위한 안전장치이자,
사용자가 지식 그래프 품질에 개입할 수 있는 human-in-the-loop 구조입니다.

## 비동기 문서 처리 구조

문서 업로드도 동기 API로 오래 기다리는 구조가 아닙니다.

사용자가 문서를 업로드하면 RAG backend는 먼저 원본 문서를 Memgraph에 저장하고,
DB가 생성한 `document_id`를 기준으로 ingest job을 만듭니다. API는 job 상태를 바로 반환하고,
실제 graph construction은 task queue와 worker pool에서 비동기로 처리됩니다.

이 구조 때문에 사용자는 문서를 하나 넣고 끝날 때까지 기다릴 필요가 없습니다. 문서를 계속
추가할 수 있고, backend는 build lane worker가 queue에서 작업을 하나씩 가져가며 처리합니다.
작업 상태는 `IngestJob`과 runtime job state를 통해 추적되고, 프론트엔드는 Graph Jobs 화면에서
queued, chunking, candidate generation, pending review, completed 같은 상태를 확인할 수 있습니다.

## Construction graph 흐름

첫 번째 graph는 document construction graph입니다.

흐름은 대략 다음과 같습니다.

1. 원본 document를 DB에 저장하고 `document_id`를 확보한다.
2. `chunking_agent`가 원본 document를 읽고 의미 단위 chunk를 만든다.
3. 각 chunk는 다시 DB에 저장되고 DB-generated `chunk_id`를 갖는다.
4. embedding dispatch service가 각 chunk에 embedding vector를 붙인다.
5. `graph_candidate_agent`가 chunk별로 병렬 실행되며, Memgraph read tools, vector search,
   text search, graph traverse, Firecrawl web search를 필요에 따라 사용한다.
6. agent는 실제 edge가 아니라 `RelationshipCandidate`를 작성한다.
7. candidate가 있으면 job은 `pending_review`가 되고, 프론트엔드 Review Queue에 올라간다.

중요한 점은 graph_candidate_agent가 단순히 현재 문서만 보는 것이 아니라, 이미 DB에 들어가 있는
다른 document와 chunk도 탐색할 수 있다는 점입니다. 그래서 서로 다른 원본 문서에서 나온 chunk끼리도
연관 관계 candidate가 만들어질 수 있습니다.

## Review graph와 Memory layer

두 번째 graph는 candidate review graph입니다.

사용자가 Review Queue에서 candidate를 approve 또는 deny하면, backend는 review task를 queue에 넣고
review worker가 처리합니다. approve된 candidate는 실제 graph edge로 materialize됩니다. deny된 candidate는
rejected 상태로 남습니다.

여기서 사용자가 reviewer note를 작성하면 이 note는 별도의 `ReviewNote` 노드로 저장되고,
해당 candidate에 `HAS_REVIEW_NOTE` edge로 연결됩니다.

그 다음 memory update 단계가 실행됩니다. memory update agent는 이번 job에서 생성된 ReviewNote와
candidate context를 읽고, 기존 Memory 문서와 합쳐서 단일 `Memory` 문서를 다시 작성합니다.

저희가 생각한 Memory는 이벤트 로그가 아니라 포스트잇에 가깝습니다. 매번 note를 그대로 끝에 붙이는
append log가 아니라, 지금까지 사용자와 작업하면서 배운 승인 기준, 거절 기준, 선호, 주의사항을 정리한
하나의 curated markdown 문서입니다.

DB 구조상으로는 다음처럼 연결됩니다.

```text
RelationshipCandidate -[:HAS_REVIEW_NOTE]-> ReviewNote -[:EVIDENCES_MEMORY]-> Memory
```

그리고 다음 candidate generation 때는 이 Memory가 tool 호출 여부와 상관없이 agent context에 자동으로
주입됩니다. 그래서 발표에서는 "이 agent는 사용자와 함께 작업하면서 점점 사용자의 기준을 학습한다"라고
설명할 수 있습니다. 엄밀하게 말하면 모델 파라미터가 학습되는 것은 아니지만, 시스템 관점에서는 memory
layer가 업데이트되면서 다음 추론과 tool 사용 기준에 반영됩니다.

## Observability와 Transparency

<!-- 발표 전체 아키텍처 다이어그램에서만 보여줄 것. 너무 깊게 설명하지 말고 시스템 투명성 포인트로 사용한다. -->

agent가 내부에서 어떤 tool을 호출하고, 어떤 단계에서 실패했는지 알 수 없으면 디버깅이 불가능합니다.
그래서 worker lifecycle과 agent event stream을 Redis Streams로 내보내고, 프론트엔드에서는 Graph Jobs와
Diagnostics Studio에서 이를 확인할 수 있게 했습니다.

이 부분은 발표에서 깊게 파고들기보다는 "agentic pipeline은 내부가 불투명해지기 쉽기 때문에,
저희는 Redis 기반 observability stream을 만들어 각 node service start/end, agent output, tool call,
tool result, error event를 볼 수 있게 만들었다" 정도로 설명하면 됩니다.

추후 LangSmith/OpenLIT telemetry를 붙이면 이 Redis 기반 운영 로그와 별개로, LangChain/LangGraph span,
tool invocation, provider latency, error를 외부 trace viewer에서 분석할 수 있습니다.

## MCP 서버 역할

RAG backend는 두 가지 역할을 동시에 합니다.

첫 번째는 프론트엔드가 사용하는 문서 업로드, job 상태 조회, review queue, memory 설정 API입니다.

두 번째는 외부 agent가 사용할 read-only MCP server입니다. 이 MCP endpoint는 Memgraph read query,
schema read, text index search, vector search, graph traverse 같은 tool을 제공합니다. 그래서 RAG graph가
구축된 뒤에는 Codex 같은 외부 MCP client가 이 서버에 붙어서 실제 Memgraph에 저장된 knowledge graph를
질의할 수 있습니다.

중요한 점은 외부 MCP는 read-only로 유지한다는 것입니다. graph를 수정하는 write tool은 pipeline 내부
agent만 사용합니다. 외부 agent는 DB를 읽고 탐색할 수 있지만, 임의로 edge나 memory를 바꾸지는 못합니다.

## 발표에서 강조할 문장

- "저희는 LLM이 만든 관계를 곧바로 지식 그래프에 반영하지 않고, 먼저 RelationshipCandidate로 저장한 뒤 Review Queue에서 검증합니다."
- "approve된 candidate만 실제 graph edge가 되고, reject된 candidate는 review artifact로 남습니다."
- "사용자 note는 ReviewNote로 저장되고, ReviewNote는 Memory의 evidence가 됩니다."
- "Memory는 append log가 아니라 다음 candidate generation agent에 항상 주입되는 curated instruction layer입니다."
- "그래서 이 시스템은 문서를 넣을수록 graph가 커지고, review를 할수록 agent의 판단 기준이 누적됩니다."
- "RAG backend는 프론트엔드 API, 비동기 worker pipeline, read-only MCP server라는 세 가지 역할을 동시에 수행합니다."

## 슬라이드에 넣을 보조 설명

- 비동기 API + task queue + worker pool:
  - 문서 업로드 API는 job을 만들고 즉시 반환한다.
  - worker가 construction graph를 실행한다.
  - review decision도 batch task로 들어가고, memory update는 review batch 마지막에 한 번 실행된다.

- Edge Candidate 방식:
  - LLM agent는 실제 edge를 직접 만들지 않는다.
  - candidate를 만들고, 사람이 승인해야 실제 edge가 된다.
  - 법률/정책 데이터처럼 신뢰성이 중요한 도메인에 적합하다.

- Memory feedback loop:
  - reviewer note가 Memory update의 근거가 된다.
  - Memory는 다음 graph candidate generation context에 자동 주입된다.
  - 반복 작업을 통해 agent의 판단 기준이 점점 프로젝트 기준에 맞춰진다.

- Observability:
  - Redis Streams로 worker lifecycle과 agent event를 기록한다.
  - FE에서 Graph Jobs와 Diagnostics Studio로 진행 상황을 볼 수 있다.
  - LangSmith/OpenLIT는 다음 단계에서 span-level telemetry를 담당한다.

