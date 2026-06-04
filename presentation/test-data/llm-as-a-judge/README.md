# LLM as a Judge Test Data

no-tool benchmark의 raw answer를 LLM judge로 판정한 결과와 실행 보조 파일을 모아 둔 디렉토리다.

## Directory Map

| Path | Purpose |
| --- | --- |
| `artifacts/tools-no/` | no-tool benchmark 답변에 대한 LLM judge 산출물 |
| `artifacts/tools-no/llm_judge_results.csv` | 답변별 LLM judge 판정 결과 |
| `artifacts/tools-no/by-model/` | `llm_judge_results.csv`를 model_id별로 나눈 CSV와 `llm_answer` 제거 버전 |
| `artifacts/tools-no/llm_judge_model_summary.csv` | model/provider별 correct/wrong 집계 |
| `artifacts/tools-no/tools_no_price_accuracy_summary.csv` | raw OpenRouter 비용과 LLM judge accuracy를 합친 price/performance 요약 |
| `artifacts/tools-no/charts/` | no-tool model별 비용 대비 LLM judge accuracy 차트 |
| `artifacts/tools-no/llm_judge_results.checkpoint.jsonl` | 재실행 이어가기를 위한 checkpoint |
| `artifacts/tools-no/llm_judge_web_cache.json` | 질문별 웹 검증 근거 cache |
| `artifacts/tools-yes/` | with-tool benchmark 답변에 대한 LLM judge 산출물 자리 |
| `tools/run_llm_judge_codex.py` | LLM judge 실행 보조 스크립트 |
| `tools/build_tools_no_price_accuracy_charts.py` | raw 비용과 judge 요약을 합쳐 price/accuracy 차트를 생성하는 스크립트 |
| `tools/llm_judge_output_schema.json` | judge 출력 JSON schema |

원본 모델 답변 CSV는 `../no-tool-benchmark/raw-results/`를 기준으로 둔다.

## Price / Accuracy Chart

no-tool benchmark의 OpenRouter 실제 token 비용과 LLM judge accuracy를 합쳐 차트를 다시 만들 때는
backend의 uv 환경에서 실행한다.

```bash
cd backend
uv run --with pandas --with numpy --with matplotlib \
  python ../presentation/test-data/llm-as-a-judge/tools/build_tools_no_price_accuracy_charts.py
```

360문항 전체가 아닌 partial raw/judge 결과가 있는 모델은 관측된 평균 token 비용과
judge accuracy를 360문항 기준으로 보정해 표시한다. judge가 아직 없는 모델은 비용만
표시하고, judge 결과가 생성되면 accuracy와 cost-per-correct 차트에 자동으로 포함된다.
