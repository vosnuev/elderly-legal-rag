from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_FILE = ROOT_DIR / "results" / "llm_validation_results.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "results" / "by_provider_csv"

QUERY_COLUMNS = [
    "testcase_id",
    "query",
    "expected_keywords",
    "reference",
    "batch",
    "difficulty",
    "special_case",
]

PROVIDER_COLUMNS = [
    "testcase_id",
    "tool_mode",
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
    parser = argparse.ArgumentParser(description="Export validation CSV into provider-grouped CSV files.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    csv.field_size_limit(sys.maxsize)
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def slug(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("/", "_").replace("-", "_").replace(".", "_")
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def provider_file_stem(row: dict[str, str]) -> str:
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
        grouped[provider_file_stem(row)].append(row)
    return dict(grouped)


def to_float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key) or 0)
    except ValueError:
        return 0.0


def build_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                row.get("model_label", ""),
                row.get("model_id", ""),
                row.get("provider_name", ""),
                row.get("provider_slug", ""),
                row.get("tool_mode", ""),
            )
        ].append(row)

    summary_rows: list[dict[str, str]] = []
    for (model_label, model_id, provider_name, provider_slug, tool_mode), items in sorted(grouped.items()):
        success_items = [row for row in items if row.get("status") == "success"]
        failed_items = [row for row in items if row.get("status") != "success"]
        latencies = [to_float(row, "latency_ms") for row in success_items if row.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        summary_rows.append(
            {
                "model_label": model_label,
                "model_id": model_id,
                "provider_name": provider_name,
                "provider_slug": provider_slug,
                "tool_mode": tool_mode,
                "success_count": str(len(success_items)),
                "failed_count": str(len(failed_items)),
                "sum_input_tokens": str(int(sum(to_float(row, "input_tokens") for row in success_items))),
                "sum_output_tokens": str(int(sum(to_float(row, "output_tokens") for row in success_items))),
                "sum_used_tokens": str(int(sum(to_float(row, "used_tokens") for row in success_items))),
                "sum_total_cost_usd": f"{sum(to_float(row, 'total_cost_usd') for row in success_items):.10f}".rstrip("0").rstrip("."),
                "avg_latency_ms": f"{avg_latency:.2f}".rstrip("0").rstrip("."),
            }
        )
    return summary_rows


def build_queries(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_testcase: dict[str, dict[str, str]] = {}
    for row in rows:
        testcase_id = row.get("testcase_id", "")
        if testcase_id and testcase_id not in by_testcase:
            by_testcase[testcase_id] = {column: row.get(column, "") for column in QUERY_COLUMNS}
    return [by_testcase[testcase_id] for testcase_id in sorted(by_testcase, key=testcase_sort_key)]


def build_provider_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {column: row.get(column, "") for column in PROVIDER_COLUMNS}
        for row in sorted(
            rows,
            key=lambda row: (
                testcase_sort_key(row.get("testcase_id", "")),
                row.get("tool_mode", ""),
            ),
        )
    ]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    _, rows = read_rows(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary_headers = [
        "model_label",
        "model_id",
        "provider_name",
        "provider_slug",
        "tool_mode",
        "success_count",
        "failed_count",
        "sum_input_tokens",
        "sum_output_tokens",
        "sum_used_tokens",
        "sum_total_cost_usd",
        "avg_latency_ms",
    ]
    write_csv(args.output_dir / "summary.csv", summary_headers, build_summary(rows))
    write_csv(args.output_dir / "queries.csv", QUERY_COLUMNS, build_queries(rows))

    for file_stem, provider_rows in sorted(group_rows(rows).items()):
        write_csv(
            args.output_dir / f"{file_stem}.csv",
            PROVIDER_COLUMNS,
            build_provider_rows(provider_rows),
        )

    print(f"wrote CSV files to: {args.output_dir}")
    print(f"provider files: {len(group_rows(rows))}")
    print(f"source rows: {len(rows)}")


if __name__ == "__main__":
    main()
