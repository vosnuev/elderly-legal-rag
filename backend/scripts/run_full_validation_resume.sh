#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONPATH="src:scripts"

uv run python scripts/run_validation_csv.py \
  --all \
  --successful-smoke-only \
  --resume \
  --skip-existing-failed-pairs

uv run python scripts/export_validation_combined_csv.py \
  --input results/llm_validation_results.csv \
  --output results/llm_validation_combined_by_provider.csv

uv run python scripts/export_validation_csvs.py \
  --input results/llm_validation_results.csv \
  --output-dir results/by_provider_csv
