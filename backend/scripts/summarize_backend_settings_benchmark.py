from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SUMMARY_FIELDS = [
    "source_file",
    "model_id",
    "provider_order",
    "allow_fallbacks",
    "langsmith_project",
    "row_count",
    "success_count",
    "failed_count",
    "sum_input_tokens",
    "sum_output_tokens",
    "sum_used_tokens",
    "sum_total_cost_usd",
    "avg_latency_ms",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize backend settings benchmark CSV files.")
    parser.add_argument("inputs", type=Path, nargs="+")
    return parser.parse_args()


def _float(value: str) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def _int(value: str) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def _source_file(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def summarize(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    success_rows = [row for row in rows if row.get("status") == "success"]
    failed_rows = [row for row in rows if row.get("status") != "success"]
    latencies = [_float(row.get("latency_ms", "")) for row in success_rows if row.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    first = rows[0] if rows else {}
    return {
        "source_file": _source_file(path),
        "model_id": first.get("model_id", ""),
        "provider_order": first.get("provider_order", ""),
        "allow_fallbacks": first.get("allow_fallbacks", ""),
        "langsmith_project": first.get("langsmith_project", ""),
        "row_count": str(len(rows)),
        "success_count": str(len(success_rows)),
        "failed_count": str(len(failed_rows)),
        "sum_input_tokens": str(sum(_int(row.get("input_tokens", "")) for row in success_rows)),
        "sum_output_tokens": str(sum(_int(row.get("output_tokens", "")) for row in success_rows)),
        "sum_used_tokens": str(sum(_int(row.get("used_tokens", "")) for row in success_rows)),
        "sum_total_cost_usd": f"{sum(_float(row.get('total_cost_usd', '')) for row in success_rows):.10f}".rstrip("0").rstrip("."),
        "avg_latency_ms": f"{avg_latency:.2f}".rstrip("0").rstrip("."),
    }


def write_summary(input_path: Path) -> Path:
    output_path = input_path.with_name(f"{input_path.stem}_summary.csv")
    row = summarize(input_path)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return output_path


def main() -> None:
    args = parse_args()
    for input_path in args.inputs:
        output_path = write_summary(input_path)
        print(f"wrote summary: {output_path}")


if __name__ == "__main__":
    main()
