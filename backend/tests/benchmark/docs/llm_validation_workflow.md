# LLM 모델 및 Tool 검증 작업 노트

작성일: 2026-06-02
담당 영역: backend

## 빠른 요약

이 작업은 `data/testcases/rag_agent_question_test_cases.md`에 있는 360개 질문을 같은 조건으로 여러 LLM/provider에 풀게 하고, 답변 품질을 나중에 `필수 키워드`, `정답 방향`, `판정 기준`으로 비교하기 위한 benchmark다.

이번에 먼저 돌리는 것은 `no_tool` benchmark다.

- 모델 입력: system prompt + testcase의 `질문`
- 모델 입력에 넣지 않는 것: `필수 키워드`, `정답 방향`, `근거 위치/참고 기준`, `LLM 키워드 판정 기준`
- 수집하는 값: answer, input/output/used token, cost, latency, provider, status, error
- 결과 파일: provider별 원본 CSV 1개 + provider별 summary CSV 1개
- 실제 RAG tool을 붙인 `with_tool` benchmark는 나중에 실제 RAG MCP tool 연결 후 별도로 실행한다.

왜 이렇게 하냐면, `no_tool`은 모델/provider 자체의 답변 능력과 비용/속도를 보는 기준선이고, `with_tool`은 RAG 검색까지 붙였을 때의 agent 성능을 보는 별도 실험이기 때문이다.

## 현재 상태 체크리스트

작성 시점: `2026-06-03 00:59:31 KST`

아이콘 의미:

- ✅ 완료
- 🔄 진행 중
- ⏳ 시작 전
- ⚠️ 주의 필요

| 상태 | 항목 | 내용 | 관련 파일 |
| --- | --- | --- | --- |
| ✅ | testcase 확인 | 360개 질문 파싱 확인. 질문은 모델 입력으로 쓰고, 정답/판정 컬럼은 CSV에만 저장 | `data/testcases/rag_agent_question_test_cases.md`, `scripts/parse_testcases.py` |
| ✅ | 기존 CSV 형식 확인 | 기존 결과와 같은 34개 원본 CSV 컬럼 유지 | `results/openai_gpt_oss_120b_cerebras_fp16.csv` |
| ✅ | summary 형식 확인 | 사용자가 보여준 `source_file,model_id,...,avg_latency_ms` 형식으로 summary 생성 | `scripts/summarize_backend_settings_benchmark.py` |
| ✅ | system prompt 수정 | testcase Judge 기준을 반영하되, benchmark 내부 문구와 정답지는 모델에게 노출하지 않음 | `src/prompt/system_prompt.j2` |
| ✅ | benchmark note 제거 | `현재는 testcase benchmark 모드...` 같은 내부 지시를 모델 입력에서 제거 | `scripts/run_backend_settings_benchmark.py` |
| ✅ | reasoning_effort 정리 | 비어 있으면 OpenRouter 요청에서 `reasoning_effort`를 제외. GMICloud tool smoke 빈 응답 문제 방지 | `src/agent/openrouter_llm.py`, `src/settings.py`, `.env` |
| ✅ | LangSmith tool call 확인 | `with_tool` smoke에서 `mock_policy_search_tool`, `rag_search_tool` run 확인 | LangSmith project `skn28-backend-agent-dev` |
| ✅ | 실제 backend tool 상태 확인 | 현재 backend tool은 mock/placeholder. 실제 RAG MCP tool은 아직 연결 전 | `src/agent/tool.py`, `README.md` |
| ✅ | clean smoke 검증 | note 제거 후 3개 provider smoke에서 내부 문구 노출 없음, 34개 컬럼 일치 확인 | `results/smoke_clean_*.csv`는 검증 후 삭제 |
| 🔄 | `gmicloud` no_tool benchmark | 321/360 rows, 실패 0. `--resume`으로 tmux 진행 중 | `results/deepseek_v4_flash_gmicloud.csv` |
| 🔄 | `siliconflow` no_tool benchmark | 252/360 rows, 실패 0. tmux 진행 중 | `results/deepseek_v4_flash_siliconflow.csv` |
| 🔄 | `deepseek` no_tool benchmark | 268/360 rows, 실패 0. tmux 진행 중 | `results/deepseek_v4_flash_deepseek.csv` |
| 🔄 | `deepinfra` no_tool benchmark | 67/360 rows, 실패 0. rate limit 때문에 더 긴 sleep/retry로 tmux 진행 중 | `results/deepseek_v4_flash_deepinfra.csv` |
| ⏳ | provider별 summary 생성 | 각 provider 360개 완료 후 `_summary.csv` 생성 | `scripts/summarize_backend_settings_benchmark.py` |
| ⏳ | with_tool benchmark | 실제 RAG MCP tool 연결 후 별도 실행 예정 | `src/agent/tool.py`, `README.md` |

최신 진행률 확인:

```bash
tmux attach -t benchmark-progress
```

4분할 로그 보기:

```bash
tmux attach -t benchmark-watch
```

tmux에서 나올 때는 benchmark가 멈추지 않도록 `Ctrl-b` 다음 `d`로 detach한다.

## 결과 파일 구조

provider별 원본 CSV:

```text
results/deepseek_v4_flash_gmicloud.csv
results/deepseek_v4_flash_siliconflow.csv
results/deepseek_v4_flash_deepseek.csv
results/deepseek_v4_flash_deepinfra.csv
```

provider별 summary CSV:

```text
results/deepseek_v4_flash_gmicloud_summary.csv
results/deepseek_v4_flash_siliconflow_summary.csv
results/deepseek_v4_flash_deepseek_summary.csv
results/deepseek_v4_flash_deepinfra_summary.csv
```

summary CSV 컬럼:

```text
source_file,model_id,provider_order,allow_fallbacks,langsmith_project,row_count,success_count,failed_count,sum_input_tokens,sum_output_tokens,sum_used_tokens,sum_total_cost_usd,avg_latency_ms
```

## 관련 파일과 코드 구조

| 파일 | 역할 | 핵심 코드/설명 |
| --- | --- | --- |
| `data/testcases/rag_agent_question_test_cases.md` | 360개 benchmark 질문과 정답/판정 기준 | 모델 입력에는 `질문`만 넣고, `키워드 정답`, `정답 방향`, `판정 기준`은 CSV 저장 및 후속 평가용으로만 사용 |
| `src/prompt/system_prompt.j2` | 모든 LLM 호출에 들어가는 기본 system prompt | 일상어를 공식 용어로 매핑, 자료 유형 혼동 금지, 조건 부족 시 확인 필요, URL/전화번호 임의 생성 금지 |
| `scripts/run_backend_settings_benchmark.py` | no_tool benchmark 실행기 | testcase 파싱, LLM 호출, token/cost/latency 수집, provider routing, retry/backoff, CSV 저장 |
| `scripts/summarize_backend_settings_benchmark.py` | 원본 CSV를 summary CSV로 요약 | row 수, 성공/실패 수, token 합계, cost 합계, 평균 latency 계산 |
| `src/agent/openrouter_llm.py` | 실제 backend agent용 OpenRouter LLM 생성 | provider order, fallback, reasoning_effort 생략 처리 |
| `src/settings.py` | backend 환경 설정 | `.env` 값을 읽고 OpenRouter/LangSmith/RAG MCP 설정 제공 |
| `src/agent/tool.py` | backend agent에 붙는 LangChain tool 목록 | 현재는 `mock_policy_search_tool`, placeholder `rag_search_tool`만 있음. 실제 RAG MCP tool은 아직 연결 전 |
| `README.md` | backend 구조와 RAG/MCP 연결 계획 | 실제 RAG tool은 FastMCP Tool Server에서 가져와 `src/agent/tool.py`에 연결해야 한다고 기록 |

`scripts/run_backend_settings_benchmark.py`의 핵심 흐름:

```python
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=testcase["query"]),
]
```

위 구조 때문에 모델은 testcase의 질문만 보고 답한다. 정답지 역할을 하는 `expected_keywords`, `reference`, `judge_criteria`는 모델에게 주지 않고 결과 CSV row에 저장한다.

rate limit 대기:

```python
sleep_seconds = min(base_sleep * (2 ** attempt), 60) + random.uniform(0, 1.5)
time.sleep(sleep_seconds)
```

정상 질문 사이 대기:

```python
if args.sleep_seconds > 0 and index < len(selected_testcases):
    time.sleep(args.sleep_seconds)
```

reasoning effort 생략:

```python
if reasoning_effort:
    llm_kwargs["reasoning_effort"] = reasoning_effort
```

`.env`에서 `BACKEND_LLM_REASONING_EFFORT=""`이면 invocation params에 `reasoning_effort`가 들어가지 않는다.

## 목적

360개의 testcase 질문을 여러 LLM 모델에 똑같이 풀게 해서 어떤 모델이 우리 서비스에 가장 적합한지 확인한다.

비유하면, 같은 시험 문제 360개를 여러 학생에게 풀게 하는 것이다.

- `testcase`: 시험 문제
- `LLM 모델`: 시험을 푸는 학생
- `tool 없음`: 학생이 머릿속 지식만으로 푸는 시험
- `tool 있음`: 학생에게 검색 도구나 교과서를 주고 푸는 시험
- `OpenRouter`: 여러 학생과 시험장을 연결해 주는 접수처
- `provider`: 실제로 모델을 실행해 주는 회사/서버
- `fallback`: 첫 번째 서버가 실패하면 다른 서버로 넘기는 예비 경로
- `token`: 문제를 읽고 답을 쓰는 데 드는 비용 단위
- `LangSmith`: 시험 과정을 녹화하고 기록하는 도구
- `CSV`: 최종 성적표와 비용 영수증

## 전체 흐름

1. testcase 360개를 backend에서 읽을 수 있는지 확인한다.
2. LLM을 tool 없이 실행하는 모드를 만든다.
3. LLM을 tool 붙여서 실행하는 모드를 만든다.
4. OpenRouter 모델과 provider 설정을 바꿔가며 실행한다.
5. LangSmith와 OpenRouter에서 토큰, 비용, 속도, tool 사용 여부를 수집한다.
6. 결과를 CSV로 저장한다.
7. 모델별 비용, 속도, 정확도, tool 사용 적절성을 비교한다.

## 실험 조합

모델 3개와 tool 모드 2개를 비교한다.

| 모델 | OpenRouter model id |
| --- | --- |
| MiniMax M3 | `minimax/minimax-m3` |
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` |
| DeepSeek V4 Flash | `deepseek/deepseek-v4-flash` |

tool 모드:

- `no_tool`: tool을 붙이지 않음
- `with_tool`: backend tool을 붙임

전체 호출 수:

```text
360 questions x 3 models x 2 tool modes = 2,160 calls
```

처음부터 2,880개를 돌리지 않는다. 먼저 질문 1개로 smoke test를 하고, 그다음 작은 샘플, 마지막에 전체 실행으로 간다.

## 진행 방식

한 번에 너무 많이 하지 않는다. 아래처럼 3개씩 진행한다.

1. 내가 할 일 3개를 확인한다.
2. 직접 해본다.
3. 문제가 없으면 다음 3개로 넘어간다.

## 지금 할 일: 1차 3개

### 1. testcase 파일 위치 확인

먼저 360개 질문이 어디에 있는지 찾아야 한다.

확인할 것:

- 파일 위치
- 파일 형식: CSV, JSON, JSONL, Excel 등
- 질문 컬럼 이름: `query`, `question`, `input` 등
- testcase id가 있는지

왜 필요한가:

backend runner가 질문을 읽으려면 파일 위치와 컬럼 이름을 알아야 한다.

### 2. 현재 backend 실행 구조 읽기

아래 파일 3개를 읽는다.

- `src/agent/graph.py`
- `src/agent/openrouter_llm.py`
- `src/agent/tool.py`

확인할 것:

- agent가 어디서 만들어지는지
- LLM 설정이 어디서 들어가는지
- tool 목록이 어디서 붙는지

현재 핵심 구조:

```text
src/agent/graph.py
  create_agent(
    model=get_chat_llm(),
    tools=get_tools(),
    system_prompt=...
  )

src/agent/openrouter_llm.py
  ChatOpenAI(...)

src/agent/tool.py
  get_tools()
```

즉, tool을 빼고 싶으면 `tools=get_tools()` 대신 `tools=[]`로 실행할 수 있는 검증용 흐름이 필요하다.

### 3. 환경 변수 확인

실험 전에 API key와 LangSmith 설정이 있어야 한다.

확인할 값:

```bash
BACKEND_OPENROUTER_API_KEY
BACKEND_OPENROUTER_MODEL
BACKEND_OPENROUTER_PROVIDER_ORDER
BACKEND_OPENROUTER_ALLOW_FALLBACKS
LANGSMITH_TRACING
LANGSMITH_API_KEY
LANGSMITH_PROJECT
```

주의:

- 실제 API key는 문서나 git에 올리지 않는다.
- `.env`에는 넣어도 되지만 `.env.example`에는 빈 값 또는 예시만 둔다.
- 전체 2,880회 호출 전에 반드시 질문 1개로 먼저 테스트한다.

## 다음에 할 일: 2차 후보

1차 3개가 끝나면 다음으로 넘어간다.

- 검증용 runner 파일 설계
- `no_tool` / `with_tool` 선택 방식 만들기
- 결과 CSV 컬럼 설계

## 진행 로그

### 1차 완료

- testcase 파일 위치 확인 완료
  - `data/testcases/rag_agent_question_test_cases.md`
  - Markdown 표 형식
  - 총 360개 testcase
  - id 컬럼: `번호`
  - 질문 컬럼: `질문`
- backend 실행 구조 확인 완료
  - `src/agent/graph.py`
  - `src/agent/openrouter_llm.py`
  - `src/agent/tool.py`
- 환경 변수 확인 단계 완료

## 지금 할 일: 2차 3개

### 1. testcase Markdown 표를 Python으로 읽기

목표는 `data/testcases/rag_agent_question_test_cases.md` 파일에서 360개 질문을 list 형태로 뽑는 것이다.

처음에는 LLM을 호출하지 않는다. 파일 파싱만 확인한다.

예상 결과:

```python
[
    {
        "testcase_id": "RAG-Q-001",
        "query": "근로기준법에서 근로자와 사용자 관련해서 기본적으로 어떤 내용을 확인해야 해?",
        "expected_keywords": "...",
        "reference": "...",
        "batch": "law_user_questions",
        "difficulty": "medium",
    },
    ...
]
```

### 2. parser 전용 작은 스크립트 만들기

추천 파일 위치:

```text
scripts/parse_testcases.py
```

이 스크립트는 다음만 한다.

- Markdown 파일 읽기
- `| RAG-Q-... | ... |` 형태의 행만 찾기
- 360개가 읽히는지 출력하기
- 앞의 3개 질문만 출력하기

아직 모델 호출은 하지 않는다.

### 3. 파싱 결과 검증하기

확인할 것:

- 총 개수가 360인지
- 첫 번째 id가 `RAG-Q-001`인지
- 질문 텍스트가 깨지지 않았는지
- `|` 때문에 컬럼이 밀리지 않았는지
- 한글이 정상 출력되는지

이 단계가 끝나야 다음에 검증 runner를 만들 수 있다.

### 2차 완료

- `scripts/parse_testcases.py` 생성 완료
- Markdown 표에서 testcase 파싱 확인 완료
- `total testcases: 360` 확인 완료
- 앞 3개 질문 출력 확인 완료

## 지금 할 일: 3차 3개

### 1. agent가 tool 사용 여부를 선택할 수 있게 만들기

현재 `src/agent/graph.py`는 항상 `tools=get_tools()`로 agent를 만든다.

검증에서는 아래 두 가지가 필요하다.

- `no_tool`: `tools=[]`
- `with_tool`: `tools=get_tools()`

그래서 `run_agent()`에 `use_tools` 옵션을 추가한다.

### 2. 기존 API 동작은 그대로 유지하기

기존 `/chat` API는 지금처럼 tool을 붙인 상태로 동작해야 한다.

그래서 기본값은 반드시 `use_tools=True`로 둔다.

```python
def run_agent(message: str, session_id: str | None = None, use_tools: bool = True) -> str:
    ...
```

이렇게 하면 기존 코드는 안 깨지고, 검증 스크립트에서만 `use_tools=False`를 넣을 수 있다.

### 3. 작은 smoke script 만들기

추천 파일 위치:

```text
scripts/validation_smoke.py
```

이 스크립트는 전체 360개를 돌리지 않는다.

처음에는 첫 번째 testcase 하나만 아래 두 모드로 실행한다.

- `no_tool`
- `with_tool`

목표는 답변 품질 평가가 아니라, 실행 구조가 되는지 확인하는 것이다.

### 3차 완료

- `src/agent/graph.py`에서 `create_main_agent(use_tools=True)` 구조 추가 완료
- `run_agent(..., use_tools=True)` 옵션 추가 완료
- 기존 API가 깨지지 않도록 기본값은 `True`로 유지
- `.env`의 `BACKEND_OPENROUTER_PROVIDER_ORDER` 형식 문제 수정 완료
- `uv run pytest` 통과 확인 완료

## 지금 할 일: 4차 3개

주의: 2026-06-02 기준으로 tool 구현이 아직 진행 중이면, 아래 smoke script보다 모델/provider/가격 확인을 먼저 한다.

### 1. validation smoke script 만들기

추천 파일 위치:

```text
scripts/validation_smoke.py
```

목표:

- testcase 파일에서 첫 번째 질문만 읽는다.
- `no_tool` 모드로 한 번 실행한다.
- `with_tool` 모드로 한 번 실행한다.

### 2. no_tool / with_tool 결과를 눈으로 비교하기

처음에는 CSV 저장까지 하지 않는다.

터미널에 아래 값만 출력한다.

- testcase id
- 질문
- tool mode
- 답변 앞부분

### 3. LangSmith trace가 남는지 확인하기

실행 후 LangSmith 프로젝트에서 trace가 생겼는지 확인한다.

확인할 것:

- `no_tool` 실행 trace
- `with_tool` 실행 trace
- tool call이 실제로 있었는지
- LLM token 사용량이 보이는지

### LangSmith가 안 보일 때 확인한 원인

`.env` 파일에 `LANGSMITH_*` 값이 있어도 LangChain/LangSmith가 자동으로 읽는다는 뜻은 아니다.

현재 backend의 `settings.py`는 pydantic-settings로 `.env`를 읽지만, 그 값들을 OS 환경변수로 export하지는 않는다.

즉, 아래처럼 Python 프로세스 안에서 값이 비어 있으면 LangSmith trace가 생기지 않는다.

```bash
PYTHONPATH=src:scripts uv run python - <<'PY'
import os

for key in ["LANGSMITH_TRACING", "LANGSMITH_PROJECT", "LANGCHAIN_CALLBACKS_BACKGROUND"]:
    print(key, os.environ.get(key))
print("LANGSMITH_API_KEY_SET", bool(os.environ.get("LANGSMITH_API_KEY")))
PY
```

해결 방법은 실행 전에 `.env` 값을 shell 환경변수로 올리는 것이다.

```bash
set -a
source .env
set +a

PYTHONPATH=src:scripts uv run python scripts/validation_smoke.py
```

또는 한 줄로 실행할 수도 있다.

```bash
set -a && source .env && set +a && PYTHONPATH=src:scripts uv run python scripts/validation_smoke.py
```

실행 전에 아래 확인 결과가 나와야 한다.

```text
LANGSMITH_TRACING='true'
LANGSMITH_PROJECT='skn28-backend-agent-dev'
LANGSMITH_API_KEY_SET True
```

## 모델/provider 선정 기록

이 문서는 모든 질문에 대한 답변 기록이 아니라, 팀원이 다음 세 가지를 빠르게 확인하기 위한 기록이다.

- 지금까지 backend에서 무엇을 준비했는지
- 왜 특정 모델과 provider를 후보로 잡았는지
- 다른 사람이 같은 기준으로 어떻게 다시 확인할 수 있는지

토큰 사용량, 실제 비용, latency, 실제 실행 provider는 최종 CSV에 기록한다. 문서에는 고정된 가격표를 길게 남기지 않는다.

### 현재 확인한 모델 후보

| 모델 | OpenRouter model id | 선정 이유 |
| --- | --- | --- |
| MiniMax M3 | `minimax/minimax-m3` | 비교 대상 모델로 요청됨. 긴 context와 tool calling 지원 여부 확인 |
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | 성능/비용 균형 비교 대상. 여러 provider fallback 가능 |
| DeepSeek V4 Flash | `deepseek/deepseek-v4-flash` | 비용/속도 비교 대상. no_tool 비용 실험과 with_tool 실험 후보를 분리해서 봐야 함 |

제외한 모델:

| 모델 | OpenRouter model id | 제외 이유 |
| --- | --- | --- |
| Qwen 3.7 Max | `qwen/qwen3.7-max` | Alibaba provider benchmark 중 OpenRouter credit/max_tokens 비용 문제가 크게 발생해 최종 후보군에서 제외 |

### provider 선택 기준

각 provider를 아래 기준으로 확인한다. 표의 기준 열은 해당 조건을 만족하는지 보여준다.

마지막 `최종 사용 추천` 열은 여러 기준을 종합했을 때 실제 실험 후보로 쓰기 좋은 provider만 ✅ 표시한다.

| 기준 | 의미 |
| --- | --- |
| endpoint | OpenRouter에서 해당 모델/provider endpoint가 확인됨 |
| tool call | `tools` parameter를 지원해서 `with_tool` 실험 가능 |
| context | testcase 질문과 system prompt를 처리하기에 충분한 context |
| max output | 답변 생성 길이가 실험에 충분하거나 확인 가능 |
| quantization | `fp4`, `fp8`, `unknown` 등 계산 정밀도 확인 가능 |
| 비용 후보 | 같은 모델 안에서 비용상 우선 검토할 만함. 상세 비용은 CSV에서 계산 |
| fallback | primary provider 실패 시 예비 provider로 둘 만함 |

### provider 가격 기준

가격 기준은 provider를 고르기 위한 사전 필터다. 실제 비용은 CSV에서 testcase별 `input_tokens`, `output_tokens`, `total_cost_usd`로 계산한다.

OpenRouter 가격은 token당 가격으로 내려오므로, 사람이 비교할 때는 1M tokens 기준으로 환산해서 본다.

```text
input_price_per_1m = prompt_price_per_token * 1,000,000
output_price_per_1m = completion_price_per_token * 1,000,000
```

provider 후보를 고를 때는 아래 기준을 사용한다.

| 모델 | ✅ 우선 후보 가격 기준 | 🟡 fallback 허용 기준 | ❌ 비싸서 제외 기준 |
| --- | --- | --- | --- |
| `minimax/minimax-m3` | 현재는 `minimax` 단일 후보 기준 | 새 provider가 생기면 기존 Minimax 대비 2배 이내 | 기존 Minimax 대비 2배 초과 |
| `deepseek/deepseek-v4-pro` | input ≤ $0.50/1M, output ≤ $1.00/1M, tools 지원 | input ≤ $1.70/1M, output ≤ $3.50/1M, tools 지원 | input > $1.70/1M 또는 output > $3.50/1M |
| `deepseek/deepseek-v4-flash` | input ≤ $0.14/1M, output ≤ $0.28/1M, tools 지원 | input ≤ $0.15/1M, output ≤ $0.30/1M, tools 지원 | input > $0.15/1M 또는 output > $0.30/1M |

예외:

- `no_tool` 비용 실험만 할 때는 tools 미지원 provider도 사용할 수 있다.
- 예를 들어 `deepseek-v4-flash`의 `baidu`는 tools 미지원이지만 가격이 낮아서 `no_tool` 비용 실험 후보로 둘 수 있다.
- `with_tool` 실험에서는 가격이 싸도 tools 미지원이면 제외한다.
- output 가격이 input 가격보다 더 중요하다. 답변이 길어질수록 output token 비용이 크게 늘기 때문이다.

아이콘 기준:

| 아이콘 | 의미 |
| --- | --- |
| ✅ | 기준 충족 |
| 🟡 | 사용 가능하지만 주의 필요 |
| 🧪 | `no_tool` 전용으로만 고려 |
| ❌ | 기준 미충족 또는 제외 권장 |
| ⚠️ | 값이 없거나 별도 확인 필요 |

### provider 체크리스트

#### MiniMax M3: `minimax/minimax-m3`

| provider | slug | endpoint | tool call | context | max output | quantization | 비용 후보 | fallback | no_tool | with_tool | 최종 사용 추천 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Minimax | `minimax` | ✅ | ✅ | ✅ | ✅ | fp8 | ✅ | ❌ 단일 후보 | ✅ | ✅ | ✅ |

#### DeepSeek V4 Pro: `deepseek/deepseek-v4-pro`

| provider | slug | endpoint | tool call | context | max output | quantization | 비용 후보 | fallback | no_tool | with_tool | 최종 사용 추천 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DeepSeek | `deepseek` | ✅ | ✅ | ✅ | ✅ | unknown | ✅ | ✅ primary | ✅ | ✅ | ✅ |
| Baidu | `baidu` | ✅ | ❌ | 🟡 | ✅ | fp8 | 🟡 | ❌ | ✅ | ❌ |  |
| DeepInfra | `deepinfra` | ✅ | ✅ | ✅ | 🟡 작음 | fp4 | 🟡 | ✅ | ✅ | ✅ |  |
| GMICloud | `gmicloud` | ✅ | ✅ | ✅ | ⚠️ 미표시 | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| StreamLake | `streamlake` | ✅ | ✅ | ✅ | ✅ | unknown | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| Novita | `novita` | ✅ | ✅ | ✅ | ✅ | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| SiliconFlow | `siliconflow` | ✅ | ✅ | ✅ | ✅ | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| Alibaba | `alibaba` | ✅ | ✅ | ✅ | ✅ | unknown | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| AtlasCloud | `atlas-cloud` | ✅ | ✅ | ✅ | ✅ | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| Venice | `venice` | ✅ | ✅ | ✅ | 🟡 작음 | unknown | ⚠️ | 🟡 | ✅ | ✅ |  |
| Parasail | `parasail` | ✅ | ✅ | ✅ | ✅ | fp8 | ⚠️ | 🟡 | ✅ | ✅ |  |
| Fireworks | `fireworks` | ✅ | ❌ | ✅ | ⚠️ 미표시 | unknown | ⚠️ | ❌ | ✅ | ❌ |  |
| DigitalOcean | `digitalocean` | ✅ | ✅ | ✅ | ⚠️ 미표시 | unknown | ⚠️ | 🟡 | ✅ | ✅ |  |
| Together | `together` | ✅ | ✅ | 🟡 | ⚠️ 미표시 | unknown | ⚠️ | 🟡 | ✅ | ✅ |  |

#### DeepSeek V4 Flash: `deepseek/deepseek-v4-flash`

| provider | slug | endpoint | tool call | context | max output | quantization | 비용 후보 | fallback | no_tool | with_tool | 최종 사용 추천 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baidu | `baidu` | ✅ | ❌ | ✅ | ✅ | fp8 | ✅ | ❌ | ✅ | ❌ | 🧪 no_tool |
| DeepInfra | `deepinfra` | ✅ | ✅ | ✅ | 🟡 작음 | fp4 | ✅ | ✅ | ✅ | ✅ | ✅ |
| GMICloud | `gmicloud` | ✅ | ✅ | ✅ | ⚠️ 미표시 | fp8 | ✅ | ✅ | ✅ | ✅ | ✅ |
| StreamLake | `streamlake` | ✅ | ❌ | ✅ | ✅ | unknown | ✅ | ❌ | ✅ | ❌ | 🧪 no_tool |
| SiliconFlow | `siliconflow` | ✅ | ✅ | ✅ | ✅ | fp8 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Alibaba | `alibaba` | ✅ | ✅ | ✅ | ✅ | unknown | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Morph | `morph` | ✅ | ✅ | 🟡 작음 | ✅ | unknown | ✅ | 🟡 | ✅ | ✅ |  |
| DeepSeek | `deepseek` | ✅ | ✅ | ✅ | ✅ | unknown | ✅ | ✅ primary | ✅ | ✅ | ✅ |
| Parasail | `parasail` | ✅ | ✅ | ✅ | ✅ | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| AtlasCloud | `atlas-cloud` | ✅ | ✅ | ✅ | ✅ | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| AkashML | `akashml` | ✅ | ✅ | ✅ | ✅ | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| Novita | `novita` | ✅ | ✅ | ✅ | ✅ | fp8 | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| DigitalOcean | `digitalocean` | ✅ | ✅ | 🟡 작음 | ⚠️ 미표시 | unknown | 🟡 | 🟡 | ✅ | ✅ |  |
| Venice | `venice` | ✅ | ✅ | ✅ | 🟡 작음 | unknown | ⚠️ | 🟡 | ✅ | ✅ |  |

### Baidu를 따로 표시한 이유

Baidu를 쓰면 안 된다는 뜻은 아니다.

다만 이번 검증은 나중에 `with_tool` 실험까지 이어져야 하므로, tool calling 지원 여부가 중요하다. OpenRouter endpoint 기준으로 Baidu는 `deepseek-v4-pro`, `deepseek-v4-flash`에서 tools 미지원으로 확인되었다.

그래서 Baidu는 아래처럼 분리한다.

| 목적 | Baidu 사용 여부 |
| --- | --- |
| `no_tool` 비용 실험 | 가능 |
| `with_tool` tool calling 실험 | 제외 권장 |
| no_tool/with_tool을 같은 provider로 공정 비교 | 제외 권장 |

추가 확인:

- `deepseek-v4-flash + baidu + allow_fallbacks=false` smoke 실행 중 OpenRouter 429가 발생했다.
- 에러 메시지: `deepseek/deepseek-v4-flash is temporarily rate-limited upstream`
- 의미: backend 코드 문제가 아니라 Baidu upstream provider가 일시적으로 rate limit 상태라는 뜻이다.
- 처리: Baidu는 실패 케이스로 기록하고, provider smoke는 다음 후보로 넘어간다.
- Baidu 자체를 꼭 검증해야 하면 잠시 후 재시도하거나 OpenRouter BYOK 설정을 확인한다.

provider 검증 원칙:

| 상황 | 처리 |
| --- | --- |
| 특정 provider 성능을 정확히 비교 | `allow_fallbacks=false` 유지, 실패하면 해당 provider 실패로 기록 |
| 서비스 동작 가능성만 확인 | `allow_fallbacks=true`로 두고 fallback 허용 |
| 429 rate limit | 코드 수정 대상 아님. CSV의 `error`에 기록 |
| 실패 run | token/cost가 없을 수 있으므로 `input_tokens`, `output_tokens`, `total_cost_usd`는 비워두고 `error`를 남김 |

### 다른 사람이 다시 확인하는 방법

provider는 OpenRouter에서 바뀔 수 있으므로, 실험 전 아래 기준으로 다시 확인한다.

1. 모델이 존재하는지 확인한다.

```bash
curl -s https://openrouter.ai/api/v1/models \
  | jq -r '.data[] | select(.id=="minimax/minimax-m3" or .id=="deepseek/deepseek-v4-pro" or .id=="deepseek/deepseek-v4-flash") | [.id,.name,.context_length] | @tsv'
```

2. provider slug를 확인한다.

```bash
curl -s https://openrouter.ai/api/v1/providers \
  | jq -r '.data[] | [.slug,.name] | @tsv'
```

3. 특정 모델의 endpoint별 provider와 tools 지원 여부를 확인한다.

```bash
curl -s https://openrouter.ai/api/v1/models/deepseek/deepseek-v4-flash/endpoints \
  | jq -r '.data.endpoints[] | [.provider_name,.context_length,.max_completion_tokens,.quantization,((.supported_parameters // []) | index("tools") != null)] | @tsv'
```

확인 후 선택한 provider는 `.env`에 넣는다.

```bash
BACKEND_OPENROUTER_MODEL="deepseek/deepseek-v4-flash"
BACKEND_OPENROUTER_PROVIDER_ORDER='["deepinfra","gmicloud","siliconflow","deepseek"]'
BACKEND_OPENROUTER_ALLOW_FALLBACKS=true
```

provider 하나만 정확히 비교할 때는 fallback을 끈다.

```bash
BACKEND_OPENROUTER_PROVIDER_ORDER='["deepseek"]'
BACKEND_OPENROUTER_ALLOW_FALLBACKS=false
```

### provider smoke 실행

provider를 손으로 하나씩 `.env`에 넣지 않는다.

`scripts/provider_smoke.py`가 OpenRouter endpoint 목록을 가져와서 각 모델/provider를 `no_tool` 첫 번째 질문으로 한 번씩 실행한다.

목적:

- provider endpoint가 실제 호출 가능한지 확인
- provider별 429, 400, timeout 같은 실패를 기록
- LangSmith에 LLM trace가 남는지 확인
- 전체 360개 실행 전에 위험한 provider를 먼저 걸러내기

실행:

```bash
cd /home/vosnuevo/workspace/SKN28-3rd-1Team/backend

PYTHONPATH=src:scripts uv run python scripts/provider_smoke.py
```

결과:

```text
results/provider_smoke_results.csv
```

주의:

- provider별 정확 검증이 목적이므로 `allow_fallbacks=false`로 실행한다.
- 실패한 provider도 CSV에 남긴다.
- 이 단계는 query 1개 smoke라서 전체 비용 계산용 결과가 아니다.
- 전체 360개 query별 token/cost 계산은 별도 full validation runner에서 수행한다.

## 결과 CSV에 들어가야 할 값

최소 컬럼:

```text
run_id,timestamp,testcase_id,query,model_id,tool_mode,provider_order,actual_provider,allow_fallbacks,input_tokens,output_tokens,total_tokens,total_cost_usd,latency_ms,tool_called,tool_names,answer,error,langsmith_run_id,openrouter_generation_id
```

결과 파일은 원본 CSV와 provider별 분할 CSV로 관리한다.

| 파일 | 목적 |
| --- | --- |
| `results/llm_validation_results.csv` | 모든 모델/provider/query 결과를 한 줄씩 저장하는 원본 결과표 |
| `results/by_provider_csv/summary.csv` | 모델/provider별 총 token, 총 비용, 평균 latency 요약 |
| `results/by_provider_csv/queries.csv` | `RAG-Q-001`~`RAG-Q-360` 질문 원문과 기대 기준 |
| `results/by_provider_csv/{model}__{provider}.csv` | 모델/provider별 query 결과표 |

주의:

- CSV는 sheet를 나눌 수 없다. 그래서 sheet 대신 CSV 파일을 여러 개로 나눈다.
- 원본 CSV는 raw data 보관용이고, `by_provider_csv` 폴더는 사람이 비교하기 위한 provider별 CSV다.

provider별 CSV는 보기 쉽게 아래 형태로 만든다.

| 구성 | 의미 |
| --- | --- |
| 행 | `RAG-Q-001`~`RAG-Q-360` testcase |
| 열 | `status`, `input_tokens`, `output_tokens`, `used_tokens`, `total_cost_usd`, `latency_ms`, `error` 등 metric |

query 전문은 provider별 CSV에 넣지 않고 `queries.csv`에서 확인한다. provider별 CSV에는 비교에 필요한 token/cost/status 중심 값만 둔다.

query별로 계산할 값:

| 값 | 의미 |
| --- | --- |
| `input_tokens` | 질문, system prompt, tool schema 등 모델에 들어간 token |
| `output_tokens` | 모델이 답변으로 생성한 token |
| `total_tokens` 또는 `used_tokens` | input + output + reasoning 등 provider가 집계한 총 사용 token |
| `input_cost_usd` | input token 비용 |
| `output_cost_usd` | output token 비용 |
| `total_cost_usd` | 해당 query 1회 실행의 총 비용 |

모델/provider별로 계산할 값:

| 값 | 의미 |
| --- | --- |
| `sum_input_tokens` | 360개 질문 전체 input token 합 |
| `sum_output_tokens` | 360개 질문 전체 output token 합 |
| `sum_total_tokens` | 360개 질문 전체 used token 합 |
| `sum_total_cost_usd` | 360개 질문 전체 비용 |
| `avg_latency_ms` | 평균 응답 시간 |
| `success_count` | 성공한 query 수 |
| `failed_count` | 실패한 query 수 |

### CSV runner 실행

실제 query별 token/cost CSV는 `scripts/run_validation_csv.py`가 만든다.

이 스크립트는 현재 `no_tool` 기준으로 실행한다. `with_tool`은 tool 구현이 완료된 뒤 별도 runner로 확장한다.

먼저 샘플 3개만 실행한다.

```bash
cd /home/vosnuevo/workspace/SKN28-3rd-1Team/backend

PYTHONPATH=src:scripts uv run python scripts/run_validation_csv.py \
  --limit 3 \
  --successful-smoke-only
```

결과:

```text
results/llm_validation_results.csv
```

특정 모델/provider만 테스트:

```bash
PYTHONPATH=src:scripts uv run python scripts/run_validation_csv.py \
  --limit 3 \
  --model-id deepseek/deepseek-v4-flash \
  --provider deepinfra
```

전체 360개 실행:

```bash
PYTHONPATH=src:scripts uv run python scripts/run_validation_csv.py \
  --all \
  --successful-smoke-only
```

주의:

- 전체 실행은 실제 API 비용이 발생한다.
- 전체 실행 전에는 반드시 `--limit 3`으로 CSV 컬럼과 LangSmith trace를 먼저 확인한다.
- `--successful-smoke-only`를 붙이면 `provider_smoke_results.csv`에서 성공한 provider만 대상으로 삼는다.
- 실패한 query도 CSV에 남기며, 실패 행은 token/cost가 비어 있고 `error`가 채워진다.
- RAG-Q-001~003 샘플에서 실패한 모델/provider 조합은 실패 행을 삭제하지 않는다.
- 다만 이후 전체 실행에서는 `--skip-existing-failed-pairs`로 해당 조합을 건너뛴다. 그래야 실패 근거는 남기고 추가 token 낭비를 막을 수 있다.

기존 결과는 유지하고, 실패 조합을 제외해 이어서 실행:

```bash
PYTHONPATH=src:scripts uv run python scripts/run_validation_csv.py \
  --all \
  --successful-smoke-only \
  --resume \
  --skip-existing-failed-pairs
```

원본 CSV를 provider별 전치 CSV 파일들로 변환:

```bash
PYTHONPATH=src:scripts uv run python scripts/export_validation_csvs.py \
  --input results/llm_validation_results.csv \
  --output-dir results/by_provider_csv
```

## 코드 작업 원칙

- 처음에는 실제 전체 실행 코드를 만들지 말고, 질문 1개만 돌리는 작은 코드부터 만든다.
- 모델/provider 설정은 코드에 박아두지 않고 환경 변수나 설정 파일로 바꿀 수 있게 한다.
- 결과는 항상 CSV로 남긴다.
- 실패한 testcase도 CSV에 남긴다.
- tool을 썼는지 여부를 반드시 기록한다.

## 2026-06-02 추가 요청 및 조치 기록

### 사용자가 요청한 내용

사용자는 `deepseek/deepseek-v4-flash`의 최종 추천 provider 4개를 대상으로 `data/testcases/rag_agent_question_test_cases.md`의 360개 질문을 모두 benchmark하고, 기존 `results/openai_gpt_oss_120b_cerebras_fp16.csv`와 같은 항목을 가진 CSV를 provider별로 만들라고 요청했다.

그 전에 다음 사항도 확인하라고 했다.

- LangSmith에서 실제 tool call이 확인되는지 볼 것
- 현재 benchmark는 `no_tool`인데 system prompt가 `rag_search_tool` 사용을 우선 고려하라고 해서 모델이 tool을 찾는 문제가 있으므로 prompt를 고칠 것
- tool이 없으면 tool을 부르지 않는 방향으로 만들 것
- 코드에 만든 OpenRouter fallback이 실제 작동할 수 있게 할 것
- query를 많이 넣을 때 rate limit이나 context 과부하처럼 보이는 거부가 생기지 않도록 대기 설정이 충돌하지 않게 할 것
- invocation params에 `reasoning_effort`가 들어가는지 확인할 것
- tool call이 안 되면 structured output 또는 `response_format` 충돌 가능성도 확인할 것
- 지금까지 사용자가 요청한 것, 실제 실행한 것, 앞으로 할 일을 이 문서에 기록할 것
- system prompt는 `data/testcases/rag_agent_question_test_cases.md`의 Judge 기준을 참고해 충돌 없이 변경할 것

### 지금까지 실행한 확인

LangSmith tool call 확인을 위해 `deepseek/deepseek-v4-flash`에 tool을 붙인 smoke를 실행했다.

확인된 provider:

| provider | 결과 |
| --- | --- |
| `deepinfra` | LangSmith에 `mock_policy_search_tool`, `rag_search_tool` run 생성 확인 |
| `siliconflow` | LangSmith에 `mock_policy_search_tool`, `rag_search_tool` run 생성 확인 |
| `deepseek` | LangSmith에 `mock_policy_search_tool`, `rag_search_tool` run 생성 확인 |
| `gmicloud` | root trace는 생성됐지만 `reasoning_effort=medium` 상태에서 content와 tool call이 비어 있음 |

GMICloud는 같은 요청에서 `reasoning_effort`를 빼고 직접 재시험하자 `finish_reason=tool_calls`와 `mock_policy_search_tool` 호출이 정상 확인됐다.

판단:

- tool schema는 GMICloud에도 전달됐다.
- structured output은 현재 코드에서 사용하지 않는다.
- `response_format`도 invocation params에 `None`으로 확인됐다.
- GMICloud의 tool call 실패는 structured output 문제가 아니라 `reasoning_effort=medium`과 provider 응답 방식의 충돌 가능성이 높다.

### invocation params 확인

기존 설정에서는 `BACKEND_LLM_REASONING_EFFORT="medium"` 때문에 ChatOpenAI invocation params에 아래 값이 들어갔다.

```text
reasoning_effort: medium
response_format: None
extra_body: {'provider': {'allow_fallbacks': ..., 'order': [...]}}
```

변경 후에는 `BACKEND_LLM_REASONING_EFFORT`가 비어 있거나 `none`, `null`, `off`, `false`이면 `reasoning_effort`를 OpenRouter 요청에서 아예 제외한다.

이유:

- `reasoning_effort`는 모델의 추론 토큰 사용 정도를 요청하는 옵션이다.
- 일부 provider에서는 reasoning 토큰만 생성하고 최종 content/tool call이 비는 현상이 생길 수 있다.
- 특히 tool call smoke에서 GMICloud가 이 패턴을 보였다.

### system prompt 변경 기준

`src/prompt/system_prompt.j2`는 `data/testcases/rag_agent_question_test_cases.md`의 Judge 기준을 반영해 변경했다.

반영한 기준:

- 일상 표현을 공식 법령명, 정책명, 자료명으로 매핑한다.
- 법령, 조례, 지역 정책, 통계/시설 현황, 일자리/채용 공고를 섞어 단정하지 않는다.
- 개인 상황 질문은 나이, 지역, 소득, 건강상태, 근무형태 등 부족한 조건을 확인해야 한다.
- 현재 지원 가능 여부, 수급 가능 여부, 법적 판단은 문서 기준 한계와 확인 필요성을 표시한다.
- tool이 제공되지 않은 실행에서는 tool 이름, tool 호출 JSON, 함수 호출 형식을 말하지 않는다.
- 검증된 URL이나 전화번호가 제공되지 않으면 새로 만들지 않는다.

### no_tool과 with_tool 분리 원칙

`no_tool` benchmark:

- LLM에 tools를 붙이지 않는다.
- system prompt도 tool 사용을 강제하지 않는다.
- `scripts/run_backend_settings_benchmark.py`는 직접 LLM을 호출하므로 tool schema가 들어가지 않는다.
- testcase의 `필수 키워드`, `정답 방향`, `판정 기준`은 모델 입력에 넣지 않고 CSV에만 저장한다.
- 모델 입력에는 system prompt와 testcase `질문`만 들어간다.
- `benchmark mode`, `tool 없음`, `rag_search_tool`, `tool 호출 JSON`, `함수 호출 형식`, `내부 사고 과정` 같은 내부 검증 문구는 모델에게 전달하지 않는다.

`with_tool` smoke 또는 향후 tool benchmark:

- `agent.graph.run_agent(..., use_tools=True)`에서만 tools를 붙인다.
- LangSmith에서 `run_type=tool` run이 생기는지 확인한다.
- GMICloud처럼 `reasoning_effort`와 tool call이 충돌할 수 있는 provider는 reasoning 옵션을 비우고 재검증한다.

### fallback 사용 원칙

provider별 성능을 정확히 비교할 때:

```bash
BACKEND_OPENROUTER_PROVIDER_ORDER='["deepinfra"]'
BACKEND_OPENROUTER_ALLOW_FALLBACKS=false
```

이 방식은 해당 provider만 평가한다. 실패하면 실패로 CSV에 남긴다.

서비스 동작 가능성이나 fallback 경로를 검증할 때:

```bash
BACKEND_OPENROUTER_PROVIDER_ORDER='["deepinfra","gmicloud","siliconflow","deepseek"]'
BACKEND_OPENROUTER_ALLOW_FALLBACKS=true
```

이 방식은 primary provider가 실패할 때 OpenRouter가 fallback provider를 사용할 수 있게 한다. 결과 CSV에서는 `provider_order`, `allow_fallbacks`, `actual_provider`를 함께 봐야 한다.

주의:

- fallback이 켜진 run은 provider별 순수 성능 비교로 쓰면 안 된다.
- fallback 검증용 CSV는 별도 파일로 두는 것이 좋다.

### 호출 사이 대기 설정

rate limit 재시도 대기는 기존처럼 유지한다.

```bash
BACKEND_VALIDATION_MAX_RETRIES=5
BACKEND_VALIDATION_RETRY_BASE_SECONDS=5
```

정상 testcase 사이에도 쉬고 싶으면 새로 추가한 옵션을 쓴다.

```bash
BACKEND_VALIDATION_SLEEP_SECONDS=1.0
```

또는 실행 인자로 지정한다.

```bash
uv run python scripts/run_backend_settings_benchmark.py \
  --all \
  --sleep-seconds 1.0
```

이 sleep은 fallback 설정과 별개로, 한 testcase 호출이 끝난 뒤 다음 testcase로 넘어가기 전에만 적용된다. 따라서 OpenRouter fallback routing과 충돌하지 않는다.

### 앞으로 실행할 순서

1. 변경된 system prompt와 `reasoning_effort` 생략 설정으로 smoke 3개를 다시 실행한다.
2. fallback 경로 검증용으로 `provider_order=["deepinfra","gmicloud","siliconflow","deepseek"]`, `allow_fallbacks=true`를 `--limit 3`으로 실행한다.
3. provider별 정확 비교용으로 4개 provider를 각각 `allow_fallbacks=false`로 360개씩 실행한다.
4. 결과 파일은 아래 이름으로 만든다.

```text
results/deepseek_v4_flash_deepinfra.csv
results/deepseek_v4_flash_gmicloud.csv
results/deepseek_v4_flash_siliconflow.csv
results/deepseek_v4_flash_deepseek.csv
```

5. 각 CSV는 기존 `openai_gpt_oss_120b_cerebras_fp16.csv`와 같은 34개 컬럼을 유지한다.

### smoke 검증 결과

변경 후 전체 실행 전 검증을 수행했다.

공통 실행 조건:

```text
model: deepseek/deepseek-v4-flash
reasoning_effort: omitted
allow_fallbacks: false
testcases: RAG-Q-001 ~ RAG-Q-003
sleep_seconds: 0.5
```

결과:

| provider | rows | success | failed | empty answer | actual_provider | 비고 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `deepinfra` | 3 | 3 | 0 | 없음 | `deepinfra` | rate limit 재시도 후 성공 |
| `gmicloud` | 3 | 3 | 0 | 없음 | `gmicloud` | reasoning 생략 후 정상 |
| `siliconflow` | 3 | 3 | 0 | 없음 | `siliconflow` | 정상 |
| `deepseek` | 3 | 3 | 0 | 없음 | `deepseek` | 정상 |

CSV 컬럼 검증:

- `results/openai_gpt_oss_120b_cerebras_fp16.csv`: 34 columns
- `results/smoke_deepseek_v4_flash_deepinfra.csv`: 34 columns, baseline과 일치
- `results/smoke_deepseek_v4_flash_gmicloud.csv`: 34 columns, baseline과 일치
- `results/smoke_deepseek_v4_flash_siliconflow.csv`: 34 columns, baseline과 일치
- `results/smoke_deepseek_v4_flash_deepseek.csv`: 34 columns, baseline과 일치

따라서 4개 provider 모두 360개 testcase 본 실행 대상으로 둔다.

### benchmark note 제거

본 실행 중 사용자가 지적한 대로 아래 별도 system note는 모델에게 알려주면 안 되는 내부 검증 지시였다.

```text
현재는 testcase benchmark 모드이며 실제 tool은 연결하지 않았다...
```

조치:

- `scripts/run_backend_settings_benchmark.py`에서 별도 `BENCHMARK_SYSTEM_NOTE`를 제거했다.
- 이후 benchmark 모델 입력은 `system_prompt.j2`와 testcase `질문`만 포함한다.
- `필수 키워드`, `정답 방향`, `근거 위치/참고 기준`, `LLM 키워드 판정 기준`은 CSV 결과 컬럼에만 저장하고 모델 입력에는 넣지 않는다.
- note가 들어간 상태로 생성된 `results/deepseek_v4_flash_gmicloud.csv` partial 결과는 본 결과에서 제외한다.

## Q&A

### Q1. 지금 benchmark의 목적은 정확히 뭐야?

360개 testcase 질문을 같은 조건으로 모델/provider별로 풀게 해서 다음을 비교하는 것이다.

- 답변이 `필수 키워드`, `정답 방향`, `판정 기준`에 맞는지
- 답변할 때 input/output/used token이 얼마나 나오는지
- 비용이 얼마나 드는지
- latency가 얼마나 걸리는지
- provider별 실패나 rate limit이 얼마나 생기는지

즉 “어떤 provider가 답변 품질, 비용, 속도 측면에서 우리 서비스에 적합한가”를 보기 위한 실험이다.

### Q2. 왜 `필수 키워드`와 `정답 방향`을 모델에게 안 줘?

그건 정답지이기 때문이다.

모델에게 정답지를 같이 주면 모델이 실제로 잘 답한 건지, 정답지를 보고 맞춘 건지 구분할 수 없다. 그래서 모델 입력에는 `질문`만 넣고, `필수 키워드`, `정답 방향`, `판정 기준`은 CSV에 저장해서 나중에 평가할 때 쓴다.

관련 코드:

```python
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=testcase["query"]),
]
```

파일: `scripts/run_backend_settings_benchmark.py`

### Q3. 지금은 no_tool이야, with_tool이야?

지금 진행 중인 것은 `no_tool` benchmark다.

`scripts/run_backend_settings_benchmark.py`는 LangChain agent를 쓰지 않고 LLM을 직접 호출한다. 따라서 tool schema가 붙지 않는다.

with_tool benchmark는 실제 RAG MCP tool 연결 후 별도 실행한다.

### Q4. 그럼 backend에 tool은 없어?

backend에 tool 코드는 있다. 다만 현재는 실제 RAG 검색 tool이 아니라 mock/placeholder다.

현재 tool:

```text
mock_policy_search_tool
rag_search_tool
```

`rag_search_tool`은 호출해도 실제 검색을 하지 않고 아래 문장을 반환한다.

```text
RAG 검색 도구는 아직 연결되지 않았습니다.
```

파일: `src/agent/tool.py`

따라서 지금 이 tool을 붙여 360개를 돌리면 RAG 성능 평가가 아니라 placeholder 결과를 보고 답하는 실험이 된다. 그래서 실제 RAG MCP tool 연결 전에는 no_tool benchmark를 먼저 돌리는 게 맞다.

### Q5. LangSmith에서 tool call은 확인됐어?

확인됐다.

`with_tool` smoke에서 LangSmith `run_type="tool"` run이 생성됐고, 아래 tool들이 error 없이 호출됐다.

```text
mock_policy_search_tool
rag_search_tool
```

이건 “backend agent가 tool schema를 붙이고 tool call을 실행할 수 있다”는 의미다. 하지만 “실제 RAG 검색이 연결됐다”는 의미는 아니다.

### Q6. LangSmith에서 tool call을 직접 확인하려면?

터미널에서:

```bash
cd /home/vosnuevo/workspace/SKN28-3rd-1Team/backend
unset LANGSMITH_API_KEY LANGCHAIN_API_KEY LANGSMITH_PROJECT LANGCHAIN_PROJECT
set -a
source .env
set +a
```

인증 확인:

```bash
uv run python - <<'PY'
from langsmith import Client

client = Client()
projects = list(client.list_projects(limit=1))
print("AUTH_OK", projects[0].name if projects else "no project")
PY
```

tool run 조회:

```bash
uv run python - <<'PY'
from datetime import datetime, timedelta, timezone
import os
from langsmith import Client

client = Client()
project = os.environ["LANGSMITH_PROJECT"]
start = datetime.now(timezone.utc) - timedelta(hours=6)

runs = list(client.list_runs(
    project_name=project,
    run_type="tool",
    start_time=start,
    limit=50,
))

print("tool_run_count:", len(runs))
for run in runs:
    print(run.start_time, run.name, "trace_id=", run.trace_id, "error=", bool(run.error))
PY
```

### Q7. `reasoning_effort`는 뭐고 왜 뺐어?

`reasoning_effort`는 모델에게 추론 토큰 사용 강도를 요청하는 옵션이다.

문제는 일부 provider에서 `reasoning_effort=medium`을 넣었을 때 content나 tool call이 비고 reasoning token만 잡히는 현상이 있었다. 특히 GMICloud tool smoke에서 이 문제가 확인됐다.

그래서 `.env`에서 아래처럼 비웠다.

```text
BACKEND_LLM_REASONING_EFFORT=""
```

그리고 코드에서는 값이 비어 있으면 OpenRouter 요청에 `reasoning_effort`를 아예 넣지 않는다.

파일:

- `src/settings.py`
- `src/agent/openrouter_llm.py`
- `scripts/run_backend_settings_benchmark.py`

### Q8. 왜 system prompt를 바꿨어?

기존 prompt에는 `rag_search_tool` 사용을 우선 고려하라는 문구가 있었다. 그런데 no_tool benchmark에서는 tool을 붙이지 않으므로 모델이 tool을 찾으려 하거나 tool 관련 표현을 답변에 섞을 수 있다.

또 testcase의 Judge 기준이 다음을 요구한다.

- 일상 표현을 공식 용어로 매핑
- 법령, 조례, 지역 정책, 시설 현황, 채용 데이터를 섞지 않기
- 개인 조건이 부족하면 확인 필요성 말하기
- 수급 가능 여부나 법적 판단을 단정하지 않기

그래서 `src/prompt/system_prompt.j2`를 이 기준에 맞춰 바꿨다.

### Q9. 왜 `현재는 testcase benchmark 모드...` note를 제거했어?

그 문장은 내부 검증 지시이기 때문이다.

모델에게 그런 문장을 주면 답변에 `benchmark`, `tool`, `rag_search_tool` 같은 내부 표현이 섞일 수 있다. 실제 사용자 질문에 답하는 조건과도 다르다.

그래서 `scripts/run_backend_settings_benchmark.py`에서 별도 `BENCHMARK_SYSTEM_NOTE`를 제거했다.

현재 모델 입력은 아래 두 개뿐이다.

```text
system_prompt.j2
testcase 질문
```

### Q10. 왜 provider별 비교에서는 fallback을 꺼?

provider 성능을 정확히 비교하려면 한 provider만 사용해야 한다.

예를 들어 `deepinfra`를 평가하는데 fallback이 켜져 있으면, 실제 응답이 `deepinfra`가 아니라 `deepseek`나 `siliconflow`에서 나올 수 있다. 그러면 provider별 비용/속도 비교가 섞인다.

그래서 provider별 정확 비교에서는:

```text
allow_fallbacks=false
provider_order=["gmicloud"]
```

서비스 안정성 테스트에서는 fallback을 켤 수 있다.

### Q11. DeepInfra에서 rate limited가 왜 나와? sleep 걸었잖아.

sleep은 두 종류다.

정상 질문 사이 대기:

```text
--sleep-seconds 20
```

rate limit 발생 후 같은 질문 재시도 대기:

```text
BACKEND_VALIDATION_MAX_RETRIES=30
BACKEND_VALIDATION_RETRY_BASE_SECONDS=20
```

DeepInfra는 upstream provider의 동시 처리량이나 quota 제한 때문에 429를 줄 수 있다. 이때 코드는 실패하지 않고 아래처럼 기다렸다가 같은 질문을 다시 시도한다.

```text
rate limited; sleep 25.2s then retry 2/30
```

즉 대기/반복은 작동한다. 다만 provider의 rate limit이 강하면 진행 속도가 느려진다.

### Q12. 왜 tmux를 여러 개 띄웠어?

provider 4개를 병렬로 돌리기 위해서다.

실행 세션:

```text
benchmark-gmicloud
benchmark-siliconflow
benchmark-deepseek
benchmark-deepinfra
```

진행률 보기:

```bash
tmux attach -t benchmark-progress
```

4분할 로그 보기:

```bash
tmux attach -t benchmark-watch
```

`benchmark-watch`는 로그를 보는 세션이다. 여기서 detach해도 실제 benchmark는 멈추지 않는다.

### Q13. tmux에서 나오면 benchmark가 멈춰?

멈추지 않는다.

나올 때는 `Ctrl-b` 다음 `d`로 detach한다.

`Ctrl-C`는 현재 보고 있는 pane의 `tail -f`를 끊을 수 있으므로 진행상황 보기에서는 권장하지 않는다.

### Q14. 지금 생성되는 CSV는 질문당 하나씩이야?

아니다.

provider 하나당 원본 CSV 하나가 생긴다. 그 CSV 안에 RAG-Q-001부터 RAG-Q-360까지 row가 쌓인다.

예:

```text
results/deepseek_v4_flash_gmicloud.csv
```

그리고 완료 후 summary 하나가 생긴다.

```text
results/deepseek_v4_flash_gmicloud_summary.csv
```

### Q15. summary CSV는 어떤 형식이야?

기존 예시와 같은 형식이다.

```text
source_file,model_id,provider_order,allow_fallbacks,langsmith_project,row_count,success_count,failed_count,sum_input_tokens,sum_output_tokens,sum_used_tokens,sum_total_cost_usd,avg_latency_ms
```

summary 생성 파일:

```text
scripts/summarize_backend_settings_benchmark.py
```

### Q16. system prompt 바꾸고 처음부터 다시 시작했어?

그렇다.

`BENCHMARK_SYSTEM_NOTE`가 들어간 partial 결과는 삭제했고, system prompt 수정 후 새 CSV를 RAG-Q-001부터 다시 만들었다.

현재 남겨야 할 no_tool 결과 파일은 아래 패턴이다.

```text
results/deepseek_v4_flash_{provider}.csv
results/deepseek_v4_flash_{provider}_summary.csv
```

### Q17. with_tool은 언제 해?

실제 RAG MCP tool이 backend에 연결된 뒤 한다.

순서:

1. 지금 no_tool benchmark 완료
2. 실제 RAG MCP tool 연결
3. LangSmith에서 tool call 확인
4. 같은 360개 testcase로 with_tool benchmark 실행
5. no_tool vs with_tool 비교

### Q18. 왜 `endpoint_tools_supported` 컬럼이 no_tool CSV에도 있어?

OpenRouter endpoint가 tools parameter를 지원하는지 기록하기 위해서다.

no_tool benchmark에서는 tool을 실제로 붙이지 않지만, 나중에 with_tool benchmark 후보를 고를 때 같은 provider가 tool calling을 지원하는지 비교할 수 있다.

### Q19. `actual_provider`는 왜 있어?

fallback이 켜진 경우 실제 응답한 provider가 primary provider와 다를 수 있기 때문이다.

provider별 정확 비교에서는 `allow_fallbacks=false`라 primary provider와 actual provider가 같아야 한다.

OpenRouter generation detail에서 provider 이름이 안 내려오는 경우가 있어, fallback이 꺼져 있고 provider가 하나뿐이면 코드에서 primary provider를 `actual_provider`로 채운다.

### Q20. 나중에 사람들이 “코드 어떻게 구성했냐”고 물으면 뭐라고 말하면 돼?

짧게 이렇게 설명하면 된다.

```text
testcase markdown을 파싱해서 질문만 모델에 넣고,
정답/판정 기준은 CSV에만 저장한다.
OpenRouter ChatOpenAI로 provider를 하나씩 고정해서 호출하고,
응답에서 token/cost/latency/generation_id를 뽑아 provider별 CSV에 저장한다.
각 provider CSV가 끝나면 summary script로 전체 token/cost/latency 합계를 만든다.
rate limit은 retry backoff로 재시도하고, 정상 호출 사이에도 sleep을 둔다.
```

핵심 파일:

```text
scripts/run_backend_settings_benchmark.py
scripts/summarize_backend_settings_benchmark.py
src/prompt/system_prompt.j2
src/agent/openrouter_llm.py
src/agent/tool.py
data/testcases/rag_agent_question_test_cases.md
```
