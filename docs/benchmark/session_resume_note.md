# Resume Note: no_tool chart report

Last updated: 2026-06-03 KST

## Done

- `docs/benchmark/no_tool_chart_report.md`
  - `전체 요약` table changed from Markdown table to HTML table.
  - `deepseek-v4-flash` model cell merged with `rowspan="4"`.
  - `deepseek-v4-pro` model cell merged with `rowspan="7"`.
  - Qwen remains excluded from this report scope.
- `docs/benchmark/analyze_no_tool_results.py`
  - Supports `docs/benchmark/artifacts/no_tool_combined_results.csv` as an input source.
  - Drops previously derived columns before recomputing routing/summary fields.
  - All chart legends are now `loc="upper left"`.
  - Bar charts 1-5 now use a black line overlay above bars.
  - Chart 3, `avg_input_tokens.png`, has a zoomed y-axis and line overlay.
- Regenerated chart PNGs under `docs/benchmark/charts/`.

## Local CSV Validation Done

- `no_tool_chart_report.md` overall summary table values matched `docs/benchmark/artifacts/no_tool_provider_summary.csv`.
- `no_tool_provider_summary.csv` matched direct recalculation from `docs/benchmark/artifacts/no_tool_combined_results.csv`.

## LangSmith Status

- LangSmith project: `skn28-backend-agent-dev`.
- Qwen is excluded from the current report and from current verification.
- Full parallel verification was attempted.
- `max_workers=6` caused LangSmith 429 rate limiting.
- Retried with `max_workers=2`, then user asked to stop and defer LangSmith verification.
- LangSmith process was stopped.

Completed LangSmith checks before stopping:

| model/provider | CSV rows | matched testcases | status mismatch | token mismatch |
| --- | ---: | ---: | ---: | ---: |
| `deepseek/deepseek-v4-flash / deepseek` | 360 | 360 | 0 | 0 |
| `deepseek/deepseek-v4-flash / deepinfra` | 360 | 360 | 0 | 0 |
| `deepseek/deepseek-v4-flash / gmicloud` | 360 | 360 | 0 | 0 |
| `deepseek/deepseek-v4-flash / siliconflow` | 360 | 360 | 0 | 0 |
| `deepseek/deepseek-v4-pro / alibaba` | 360 | 360 | 0 | 0 |
| `deepseek/deepseek-v4-pro / atlas-cloud` | 360 | 360 | 0 | 0 |

Remaining LangSmith checks:

- `deepseek/deepseek-v4-pro / deepseek`
- `deepseek/deepseek-v4-pro / gmicloud`
- `deepseek/deepseek-v4-pro / novita`
- `deepseek/deepseek-v4-pro / siliconflow`
- `deepseek/deepseek-v4-pro / streamlake`
- `openai/gpt-oss-120b / cerebras`

Suggested resume approach:

- Use low concurrency (`max_workers=1` or `2`) to avoid LangSmith 429.
- Keep Qwen excluded unless the report scope is explicitly changed.
