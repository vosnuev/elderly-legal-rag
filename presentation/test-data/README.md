# Presentation Test Data

프레젠테이션과 평가 설명에 사용할 테스트 케이스, 벤치마크 결과, 차트 산출물을 모아 둔 디렉토리다.

## Directory Map

| Path | Purpose |
| --- | --- |
| `rag-agent-question-cases/rag_agent_question_test_cases_360.md` | RAG Agent 평가용 360개 질문, 키워드 정답, 근거 위치, 판정 기준 |
| `no-tool-benchmark/no_tool_benchmark_report.md` | model/provider별 no-tool 벤치마크 통합 분석 리포트 |
| `no-tool-benchmark/raw-results/` | provider별 원본 실행 결과 CSV |
| `no-tool-benchmark/artifacts/` | 통합/요약/실패/routing 분석 CSV |
| `no-tool-benchmark/charts/` | 발표에 사용할 비용, latency, token 비교 차트 |
| `no-tool-benchmark/results/benchmark_all_model_by_provider.xlsx` | 전체 provider 결과를 묶은 Excel 파일 |
| `no-tool-benchmark/tools/analyze_no_tool_results.py` | raw CSV에서 artifacts/charts를 재생성하는 분석 스크립트 |
| `no-tool-benchmark/tools/run_qwen37_max_no_tool_benchmark.py` | Qwen3.7 Max / Alibaba no-tool raw CSV 생성 스크립트. 기본값은 1건 smoke |
| `llm-as-a-judge/` | no-tool raw answer의 LLM judge 판정 결과, checkpoint, web cache, 관련 보조 파일 |

LLM judge 산출물:

- `llm-as-a-judge/artifacts/tools-no/llm_judge_results.csv`: 4개 no-tool model/provider의 1,280개 답변별 `llm_answer`, token/cost/latency, `judge_result`, `judge_reason`, 웹 검증 메모.
- `llm-as-a-judge/artifacts/tools-no/llm_judge_model_summary.csv`: model/provider별 correct/wrong 집계와 평균 token/cost/latency.
- `llm-as-a-judge/artifacts/tools-no/wrong_type_enum.csv`: no-tool 오답 유형 enum과 전체 count/ratio.
- `llm-as-a-judge/artifacts/tools-no/wrong_type_summary.csv`: model/provider별 no-tool 오답 유형 count/ratio.
- `llm-as-a-judge/artifacts/tools-yes/wrong-questions/`: no-tool 오답만 모은 with-tool 실행 후보 데이터셋.
- `llm-as-a-judge/artifacts/tools-no/charts/`: OpenRouter 실제 비용과 LLM judge accuracy를 합친 price/performance 차트.

Qwen3.7 Max no-tool smoke:

```bash
python3 presentation/test-data/no-tool-benchmark/tools/run_qwen37_max_no_tool_benchmark.py
```

기본 smoke 결과는 `no-tool-benchmark/artifacts/smoke/qwen_qwen3_7_max_alibaba_smoke.csv`에 저장된다. 360개 전체를 raw-results 형식으로 저장할 때만 `--all`을 붙인다.

과거 benchmark 작업 노트는 발표 자료가 아니라 작업 로그 성격이라 이 묶음에는 포함하지 않는다.
