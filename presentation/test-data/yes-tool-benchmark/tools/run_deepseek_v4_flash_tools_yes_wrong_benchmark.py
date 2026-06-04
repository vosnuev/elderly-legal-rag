from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BENCHMARK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
WRONG_QUESTIONS_PATH = (
    REPO_ROOT
    / "presentation"
    / "test-data"
    / "llm-as-a-judge"
    / "artifacts"
    / "tools-yes"
    / "wrong-questions"
    / "wrong_questions__deepseek_deepseek_v4_flash.csv"
)
DEFAULT_SMOKE_OUTPUT = (
    BENCHMARK_DIR
    / "artifacts"
    / "smoke"
    / "deepseek_v4_flash_tools_yes_wrong_smoke.csv"
)
DEFAULT_FULL_OUTPUT = (
    BENCHMARK_DIR / "raw-results" / "deepseek_v4_flash_tools_yes_wrong.csv"
)

TARGET_MODEL_ID = "deepseek/deepseek-v4-flash"
TARGET_PROVIDER_ORDER = ["deepseek"]
DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000"

FIELDNAMES = [
    "timestamp",
    "testcase_id",
    "query_reference",
    "answer",
    "tool_call_count",
    "tool_calls",
    "source_count",
    "sources",
    "target_model_id",
    "expected_provider_order",
    "backend_base_url",
    "batch",
    "difficulty",
    "special_case",
    "no_tool_model_id",
    "no_tool_provider",
    "no_tool_actual_provider",
    "no_tool_judge_result",
    "no_tool_judge_reason",
    "no_tool_total_cost_usd",
    "no_tool_latency_ms",
    "latency_ms",
    "status",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a backend /chat tools-yes benchmark over DeepSeek V4 Flash "
            "no-tool wrong questions."
        )
    )
    parser.add_argument("--input-csv", type=Path, default=WRONG_QUESTIONS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--backend-base-url", default=DEFAULT_BACKEND_BASE_URL)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--stop-after-failures", type=int, default=1)
    parser.add_argument("--target-model-id", default=TARGET_MODEL_ID)
    parser.add_argument(
        "--provider-order",
        default=json.dumps(TARGET_PROVIDER_ORDER),
        help="Expected backend provider order, recorded for traceability.",
    )
    return parser.parse_args()


def provider_order(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("--provider-order must be a JSON string list")
    return parsed


def load_wrong_questions(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    return rows


def query_reference(testcase: dict[str, str]) -> str:
    return "\n".join(
        [
            f"query: {testcase['question']}",
            f"expected_keywords: {testcase.get('expected_keywords', '')}",
            f"reference: {testcase.get('reference', '')}",
            f"judge_criteria: {testcase.get('judge_criteria', '')}",
        ]
    )


def request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def healthcheck(base_url: str, timeout: int) -> dict[str, Any]:
    return request_json("GET", f"{base_url.rstrip('/')}/health", timeout=timeout)


def post_chat(
    *,
    base_url: str,
    testcase: dict[str, str],
    timeout_seconds: int,
    target_model_id: str,
) -> dict[str, Any]:
    payload = {
        "session_id": f"tools-yes-{target_model_id}-{testcase['question_number']}",
        "message": testcase["question"],
        "metadata": {
            "benchmark": "tools-yes-wrong-only",
            "target_model_id": target_model_id,
            "question_number": testcase["question_number"],
            "no_tool_model_id": testcase.get("model_id", ""),
        },
    }
    return request_json(
        "POST",
        f"{base_url.rstrip('/')}/chat",
        payload=payload,
        timeout=timeout_seconds,
    )


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def error_summary(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return f"HTTPError {exc.code}: {body[:500]}"
    return f"{exc.__class__.__name__}: {str(exc)[:500]}"


def run_one(
    *,
    testcase: dict[str, str],
    base_url: str,
    target_model_id: str,
    order: list[str],
    timeout_seconds: int,
) -> dict[str, str]:
    started = time.perf_counter()
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "testcase_id": testcase["question_number"],
        "query_reference": query_reference(testcase),
        "answer": "",
        "tool_call_count": "",
        "tool_calls": "",
        "source_count": "",
        "sources": "",
        "target_model_id": target_model_id,
        "expected_provider_order": compact_json(order),
        "backend_base_url": base_url.rstrip("/"),
        "batch": testcase.get("batch", ""),
        "difficulty": testcase.get("difficulty", ""),
        "special_case": testcase.get("special_case", ""),
        "no_tool_model_id": testcase.get("model_id", ""),
        "no_tool_provider": testcase.get("provider", ""),
        "no_tool_actual_provider": testcase.get("actual_provider", ""),
        "no_tool_judge_result": testcase.get("no_tool_judge_result", ""),
        "no_tool_judge_reason": testcase.get("no_tool_judge_reason", ""),
        "no_tool_total_cost_usd": testcase.get("no_tool_total_cost_usd", ""),
        "no_tool_latency_ms": testcase.get("no_tool_latency_ms", ""),
        "latency_ms": "",
        "status": "",
        "error": "",
    }

    try:
        response = post_chat(
            base_url=base_url,
            testcase=testcase,
            timeout_seconds=timeout_seconds,
            target_model_id=target_model_id,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        tool_calls = response.get("tool_calls") or []
        sources = response.get("sources") or []
        row.update(
            {
                "answer": str(response.get("answer") or ""),
                "tool_call_count": str(len(tool_calls)),
                "tool_calls": compact_json(tool_calls),
                "source_count": str(len(sources)),
                "sources": compact_json(sources),
                "latency_ms": str(latency_ms),
                "status": "success",
            }
        )
    except Exception as exc:
        row.update(
            {
                "latency_ms": str(int((time.perf_counter() - started) * 1000)),
                "status": "failed",
                "error": error_summary(exc),
            }
        )

    return row


def existing_success_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["testcase_id"]
            for row in csv.DictReader(handle)
            if row.get("status") == "success" and row.get("testcase_id")
        }


def main() -> None:
    args = parse_args()
    order = provider_order(args.provider_order)
    output = args.output or (DEFAULT_FULL_OUTPUT if args.all else DEFAULT_SMOKE_OUTPUT)
    selected = load_wrong_questions(args.input_csv)
    if not args.all:
        selected = selected[: args.limit]
    if args.resume:
        completed = existing_success_ids(output)
        selected = [row for row in selected if row["question_number"] not in completed]

    print(f"backend_base_url: {args.backend_base_url.rstrip('/')}")
    print(f"target_model_id: {args.target_model_id}")
    print(f"expected_provider_order: {order}")
    print(f"input_csv: {args.input_csv}")
    print(f"testcases selected: {len(selected)}")
    print(f"output: {output}")
    if args.dry_run:
        return

    health = healthcheck(args.backend_base_url, min(args.timeout_seconds, 30))
    print(f"backend_health: {health}")

    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume and output.exists() else "w"

    with output.open(mode, encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if mode == "w" or output.stat().st_size == 0:
            writer.writeheader()

        consecutive_failures = 0
        for index, testcase in enumerate(selected, start=1):
            print(f"[{index}/{len(selected)}] {testcase['question_number']}", flush=True)
            row = run_one(
                testcase=testcase,
                base_url=args.backend_base_url,
                target_model_id=args.target_model_id,
                order=order,
                timeout_seconds=args.timeout_seconds,
            )
            writer.writerow(row)
            handle.flush()
            print(
                f"  -> {row['status']} tool_calls={row['tool_call_count']}"
                + (f": {row['error']}" if row["error"] else ""),
                flush=True,
            )
            consecutive_failures = (
                consecutive_failures + 1 if row["status"] == "failed" else 0
            )
            if (
                args.stop_after_failures > 0
                and consecutive_failures >= args.stop_after_failures
            ):
                print(
                    f"stopping after {consecutive_failures} consecutive failures",
                    flush=True,
                )
                break
            if args.sleep_seconds > 0 and index < len(selected):
                time.sleep(args.sleep_seconds)

    print(f"wrote CSV: {output}")


if __name__ == "__main__":
    csv.field_size_limit(sys.maxsize)
    main()
