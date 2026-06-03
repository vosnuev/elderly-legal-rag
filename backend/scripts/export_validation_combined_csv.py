from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_FILE = ROOT_DIR / "results" / "llm_validation_results.csv"
DEFAULT_OUTPUT_FILE = ROOT_DIR / "results" / "llm_validation_combined_by_provider.csv"

TRANSPOSE_METRICS = [
    "status",
    "actual_provider",
    "input_tokens",
    "output_tokens",
    "used_tokens",
    "input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
    "latency_ms",
    "openrouter_generation_id",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export validation results to one provider-grouped CSV."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def slug(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("/", "_").replace("-", "_").replace(".", "_")
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def provider_sheet_name(row: dict[str, str]) -> str:
    model = row.get("sheet_name") or slug(row.get("model_id", "model"))
    provider = slug(row.get("provider_slug") or row.get("provider_name", "provider"))
    return f"{model}__{provider}"


def testcase_sort_key(testcase_id: str) -> tuple[int, str]:
    match = re.search(r"(\d+)$", testcase_id)
    if match:
        return int(match.group(1)), testcase_id
    return 10**9, testcase_id


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[provider_sheet_name(row)].append(row)
    return dict(grouped)


def build_combined_rows(rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    testcase_ids = sorted(
        {row.get("testcase_id", "") for row in rows if row.get("testcase_id")},
        key=testcase_sort_key,
    )
    headers = [
        "sheet",
        "model_label",
        "model_id",
        "provider_name",
        "provider_slug",
        "tool_mode",
        "metric",
        *testcase_ids,
    ]

    combined_rows: list[dict[str, str]] = []
    for sheet, provider_rows in sorted(group_rows(rows).items()):
        provider_testcase_ids = sorted(
            {row.get("testcase_id", "") for row in provider_rows if row.get("testcase_id")},
            key=testcase_sort_key,
        )
        tool_modes = sorted(
            {row.get("tool_mode", "unknown") or "unknown" for row in provider_rows}
        )
        by_mode_and_testcase = {
            (row.get("tool_mode", "unknown") or "unknown", row.get("testcase_id", "")): row
            for row in provider_rows
            if row.get("testcase_id")
        }
        first = provider_rows[0]

        for tool_mode in tool_modes:
            for metric in TRANSPOSE_METRICS:
                output_row = {
                    "sheet": sheet,
                    "model_label": first.get("model_label", ""),
                    "model_id": first.get("model_id", ""),
                    "provider_name": first.get("provider_name", ""),
                    "provider_slug": first.get("provider_slug", ""),
                    "tool_mode": tool_mode,
                    "metric": metric,
                }
                for testcase_id in provider_testcase_ids:
                    source = by_mode_and_testcase.get((tool_mode, testcase_id), {})
                    output_row[testcase_id] = source.get(metric, "")
                combined_rows.append(output_row)

    return headers, combined_rows


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input)
    headers, combined_rows = build_combined_rows(rows)
    write_csv(args.output, headers, combined_rows)
    print(f"wrote CSV: {args.output}")
    print(f"source rows: {len(rows)}")
    print(f"combined rows: {len(combined_rows)}")


if __name__ == "__main__":
    main()
