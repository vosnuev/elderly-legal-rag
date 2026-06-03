# no_tool Benchmark 결과 분석 정리

작성일: 2026-06-03

## 목적

`docs/benchmark/results`에 저장된 no_tool benchmark CSV를 pandas/numpy로 전처리하고, model/provider별 토큰 사용량, 비용, latency, 실패율을 비교한다.

현재 이 문서의 범위는 `no_tool` benchmark다.

- 실제 RAG tool은 연결하지 않았다.
- 각 모델은 system prompt와 testcase 질문만 보고 답했다.
- `with_tool` 결과와 섞어 비교하면 안 된다.
- Qwen 3.7 Max는 비용 문제로 후보군에서 제외했다.

## 입력 데이터

분석 대상 폴더:

```bash
/home/vosnuevo/workspace/SKN28-3rd-1Team/docs/benchmark/results
```

현재 분석 대상 CSV:

```text
deepseek_v4_flash_deepinfra.csv
deepseek_v4_flash_deepseek.csv
deepseek_v4_flash_gmicloud.csv
deepseek_v4_flash_siliconflow.csv
deepseek_v4_pro_alibaba.csv
deepseek_v4_pro_atlas_cloud.csv
deepseek_v4_pro_deepseek.csv
deepseek_v4_pro_gmicloud.csv
deepseek_v4_pro_novita.csv
deepseek_v4_pro_siliconflow.csv
deepseek_v4_pro_streamlake.csv
openai_gpt_oss_120b_cerebras_fp16.csv
```

## CSV 구조

모든 결과 CSV는 아래 컬럼 순서를 사용한다.

```text
timestamp, testcase_id, query_reference, answer, input_price_per_1m, output_price_per_1m, input_tokens, output_tokens, used_tokens, input_cost_usd, output_cost_usd, total_cost_usd, batch, difficulty, special_case, model_id, provider_order, primary_provider_slug, primary_provider_quantization, actual_provider, allow_fallbacks, endpoint_tools_supported, context_length, max_completion_tokens, quantization, openrouter_generation_id, latency_ms, langsmith_project, langsmith_tags, status, error
```

`query_reference`에는 기존 `query`, `expected_keywords`, `reference`, `judge_criteria`를 한 컬럼으로 묶었다.

## 전처리 원칙

1. `docs/benchmark/results/*.csv`를 읽되 `summary`, `qwen`, `smoke`, `raw` 파일은 제외한다.
2. 숫자 컬럼은 `pd.to_numeric(..., errors="coerce")`로 변환한다.
3. 평균 token, 비용, latency는 `status == "success"` row 기준으로 계산한다.
4. 실패 row는 평균 계산에서 제외하되, `failed_count`와 `failure_report`에 남긴다.
5. provider별 순수 비교는 routing 검증을 통과한 provider만 기준으로 본다.
6. routing 검증 통과 조건은 `allow_fallbacks=false`이고, 성공 row의 `actual_provider`가 `primary_provider_slug`와 일치하는 것이다.
7. `query_reference` 안의 정답 기준은 모델 입력이 아니라 후속 평가 기준이다.

percentile 계산 방식:

- `p95_latency_ms`, `p95_used_tokens`는 `numpy.percentile(..., 95)` 기본값인 linear 보간 방식으로 계산한다.
- latency 평균과 p95는 성공 row 기준이다.

## 분석 스크립트

```bash
cd /home/vosnuevo/workspace/SKN28-3rd-1Team/backend
uv run python ../docs/benchmark/analyze_no_tool_results.py --results-dir ../docs/benchmark/results
```

## Provider별 기본 지표

| # | model_id | provider | success | failed | avg_input_tokens | avg_output_tokens | avg_used_tokens | avg_cost_usd | total_cost_usd | avg_latency_ms | p95_latency_ms |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #1 | `openai/gpt-oss-120b` | `cerebras` | 360/360 | 0 | 893.8 | 1,080.7 | 1,974.5 | 0.00112336 | 0.40440835 | 1,411 | 2,106 |
| #2 | `deepseek/deepseek-v4-flash` | `deepinfra` | 360/360 | 0 | 936.4 | 525.8 | 1,462.2 | 0.00019778 | 0.07120136 | 21,240 | 40,612 |
| #3 | `deepseek/deepseek-v4-flash` | `deepseek` | 360/360 | 0 | 936.4 | 1,222.9 | 2,159.4 | 0.00035059 | 0.12621101 | 12,385 | 18,371 |
| #4 | `deepseek/deepseek-v4-flash` | `siliconflow` | 360/360 | 0 | 936.4 | 1,187.5 | 2,123.9 | 0.00039211 | 0.14115901 | 14,452 | 21,647 |
| #5 | `deepseek/deepseek-v4-flash` | `gmicloud` | 360/360 | 0 | 938.4 | 1,159.5 | 2,097.9 | 0.00030621 | 0.11023653 | 16,603 | 25,158 |
| #6 | `deepseek/deepseek-v4-pro` | `streamlake` | 360/360 | 0 | 936.4 | 1,495.8 | 2,432.3 | 0.00496864 | 1.78871151 | 17,393 | 27,379 |
| #7 | `deepseek/deepseek-v4-pro` | `deepseek` | 359/360 | 1 | 936.5 | 1,472.4 | 2,408.9 | 0.00130400 | 0.46813639 | 34,204 | 56,152 |
| #8 | `deepseek/deepseek-v4-pro` | `gmicloud` | 360/360 | 0 | 941.8 | 1,361.1 | 2,302.9 | 0.00414434 | 1.49196184 | 32,685 | 60,376 |
| #9 | `deepseek/deepseek-v4-pro` | `alibaba` | 360/360 | 0 | 936.4 | 1,542.5 | 2,478.9 | 0.00564091 | 2.03072712 | 28,049 | 52,131 |
| #10 | `deepseek/deepseek-v4-pro` | `novita` | 360/360 | 0 | 938.0 | 1,476.6 | 2,414.6 | 0.00516377 | 1.85895712 | 34,303 | 58,748 |
| #11 | `deepseek/deepseek-v4-pro` | `siliconflow` | 360/360 | 0 | 936.4 | 1,446.5 | 2,383.0 | 0.00543860 | 1.95789440 | 34,998 | 62,825 |
| #12 | `deepseek/deepseek-v4-pro` | `atlas-cloud` | 360/360 | 0 | 936.4 | 1,471.1 | 2,407.5 | 0.00601472 | 2.16529972 | 40,263 | 73,860 |

## 차트 리포트

상세 해석과 후보 판단표는 `docs/benchmark/no_tool_chart_report.md`를 본다.
