from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BENCHMARK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_DIR = REPO_ROOT / "backend"
QUESTION_SET_PATH = (
    BENCHMARK_DIR.parent
    / "rag-agent-question-cases"
    / "rag_agent_question_test_cases_360.md"
)
SYSTEM_PROMPT_PATH = BACKEND_DIR / "src" / "prompt" / "system_prompt.j2"
DEFAULT_SMOKE_OUTPUT = (
    BENCHMARK_DIR / "artifacts" / "smoke" / "qwen_qwen3_7_max_alibaba_smoke.csv"
)
DEFAULT_FULL_OUTPUT = BENCHMARK_DIR / "raw-results" / "qwen_qwen3_7_max_alibaba.csv"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MODEL_ID = "qwen/qwen3.7-max"
PROVIDER_ORDER = ["alibaba"]

FIELDNAMES = [
    "timestamp",
    "testcase_id",
    "query_reference",
    "answer",
    "input_price_per_1m",
    "output_price_per_1m",
    "input_tokens",
    "output_tokens",
    "used_tokens",
    "input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
    "batch",
    "difficulty",
    "special_case",
    "model_id",
    "provider_order",
    "primary_provider_slug",
    "primary_provider_quantization",
    "actual_provider",
    "allow_fallbacks",
    "endpoint_tools_supported",
    "context_length",
    "max_completion_tokens",
    "quantization",
    "openrouter_generation_id",
    "latency_ms",
    "langsmith_project",
    "langsmith_tags",
    "status",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Qwen3.7 Max no-tool benchmark smoke/full CSV."
    )
    parser.add_argument("--question-set", type=Path, default=QUESTION_SET_PATH)
    parser.add_argument("--system-prompt", type=Path, default=SYSTEM_PROMPT_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-base-seconds", type=float, default=5.0)
    parser.add_argument("--stop-after-failures", type=int, default=1)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--provider-order", default=json.dumps(PROVIDER_ORDER))
    parser.add_argument("--allow-fallbacks", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=0)
    return parser.parse_args()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def api_key() -> str:
    value = os.environ.get("BACKEND_OPENROUTER_API_KEY") or os.environ.get(
        "OPENROUTER_API_KEY"
    )
    if not value:
        raise RuntimeError(
            "OPENROUTER_API_KEY or BACKEND_OPENROUTER_API_KEY is required."
        )
    return value


def request_json(
    method: str,
    url: str,
    *,
    key: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_markdown_table(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("| RAG-Q-"):
            continue

        columns = [column.strip() for column in line.strip("|").split("|")]
        if len(columns) != 8:
            raise ValueError(f"Unexpected testcase row shape: {line[:160]}")
        rows.append(
            {
                "testcase_id": columns[0],
                "query": columns[1],
                "expected_keywords": columns[2],
                "reference": columns[3],
                "judge_criteria": columns[4],
                "batch": columns[5],
                "difficulty": columns[6],
                "special_case": columns[7],
            }
        )
    return rows


def query_reference(testcase: dict[str, str]) -> str:
    return "\n".join(
        [
            f"query: {testcase['query']}",
            f"expected_keywords: {testcase['expected_keywords']}",
            f"reference: {testcase['reference']}",
            f"judge_criteria: {testcase['judge_criteria']}",
        ]
    )


def provider_order(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("--provider-order must be a JSON string list")
    return parsed


def primary_provider(order: list[str]) -> tuple[str, str]:
    if not order:
        return "", ""
    slug, _, quantization = order[0].partition("/")
    return slug, quantization


def price_per_1m(value: Any) -> float:
    if value in {None, ""}:
        return 0.0
    return float(value) * 1_000_000


def compact_float(value: Any) -> str:
    if value in {None, ""}:
        return ""
    try:
        return f"{float(value):.10f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def provider_slug_map() -> dict[str, str]:
    try:
        data = request_json("GET", f"{OPENROUTER_BASE_URL}/providers", timeout=30)
    except Exception:
        return {}
    return {
        str(item.get("name", "")).lower(): str(item.get("slug", ""))
        for item in data.get("data", [])
    }


def endpoint_metadata(model_id: str, order: list[str]) -> dict[str, Any]:
    primary_slug, primary_quantization = primary_provider(order)
    slugs_by_name = provider_slug_map()
    url = f"{OPENROUTER_BASE_URL}/models/{model_id}/endpoints"
    try:
        data = request_json("GET", url, timeout=30)
    except Exception:
        return {}

    matches: list[dict[str, Any]] = []
    for endpoint in data.get("data", {}).get("endpoints", []):
        provider_name = str(endpoint.get("provider_name", ""))
        provider_slug = (
            endpoint.get("provider_slug")
            or slugs_by_name.get(provider_name.lower())
            or provider_name.lower().split()[0]
        )
        if provider_slug == primary_slug:
            matches.append(endpoint)

    if primary_quantization:
        for endpoint in matches:
            if (
                str(endpoint.get("quantization") or "").lower()
                == primary_quantization.lower()
            ):
                return endpoint
    return matches[0] if matches else {}


def response_usage(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "used_tokens": total_tokens,
    }


def generation_details(generation_id: str, key: str) -> dict[str, Any]:
    if not generation_id:
        return {}
    time.sleep(0.5)
    query = urllib.parse.urlencode({"id": generation_id})
    try:
        data = request_json(
            "GET",
            f"{OPENROUTER_BASE_URL}/generation?{query}",
            key=key,
            timeout=30,
        )
    except Exception:
        return {}
    return data.get("data") or {}


def actual_provider_slug(
    generation: dict[str, Any],
    primary_slug: str,
    order: list[str],
    allow_fallbacks: bool,
) -> str:
    provider_name = str(generation.get("provider_name") or "")
    if provider_name:
        mapped = provider_slug_map().get(provider_name.lower())
        if mapped:
            return mapped
        return provider_name.lower().split()[0]
    if not allow_fallbacks or len(order) == 1:
        return primary_slug
    return ""


def retryable_error(exc: Exception) -> bool:
    text = f"{exc.__class__.__name__}: {exc}".lower()
    return any(
        marker in text
        for marker in ["429", "rate limit", "rate-limit", "rate_limited", "rate-limited"]
    )


def call_openrouter(
    *,
    key: str,
    model_id: str,
    order: list[str],
    allow_fallbacks: bool,
    system_prompt: str,
    question: str,
    temperature: float,
    timeout_seconds: int,
    max_retries: int,
    retry_base_seconds: float,
    max_tokens: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "temperature": temperature,
        "provider": {
            "order": order,
            "allow_fallbacks": allow_fallbacks,
        },
    }
    if max_tokens > 0:
        payload["max_tokens"] = max_tokens

    for attempt in range(max_retries + 1):
        try:
            return request_json(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                key=key,
                payload=payload,
                timeout=timeout_seconds,
            )
        except Exception as exc:
            if not retryable_error(exc) or attempt >= max_retries:
                raise
            sleep_seconds = min(retry_base_seconds * (2**attempt), 60) + random.uniform(
                0,
                1.5,
            )
            print(
                f"  -> rate limited; sleep {sleep_seconds:.1f}s then retry {attempt + 1}/{max_retries}",
                flush=True,
            )
            time.sleep(sleep_seconds)

    raise RuntimeError("unreachable retry path")


def answer_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    return str(content or "")


def error_summary(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        return f"HTTPError {exc.code}: {body[:500]}"
    return f"{exc.__class__.__name__}: {str(exc)[:500]}"


def run_one(
    *,
    key: str,
    testcase: dict[str, str],
    model_id: str,
    order: list[str],
    allow_fallbacks: bool,
    metadata: dict[str, Any],
    system_prompt: str,
    args: argparse.Namespace,
) -> dict[str, str]:
    started = time.perf_counter()
    primary_slug, primary_quantization = primary_provider(order)
    pricing = metadata.get("pricing") or {}
    supported_parameters = metadata.get("supported_parameters") or []
    input_price = price_per_1m(pricing.get("prompt"))
    output_price = price_per_1m(pricing.get("completion"))
    tags = [
        "qwen37-max-no-tool-benchmark",
        model_id,
        primary_slug or "provider-unspecified",
        testcase["testcase_id"],
    ]

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "testcase_id": testcase["testcase_id"],
        "query_reference": query_reference(testcase),
        "answer": "",
        "input_price_per_1m": f"{input_price:.8g}",
        "output_price_per_1m": f"{output_price:.8g}",
        "input_tokens": "",
        "output_tokens": "",
        "used_tokens": "",
        "input_cost_usd": "",
        "output_cost_usd": "",
        "total_cost_usd": "",
        "batch": testcase["batch"],
        "difficulty": testcase["difficulty"],
        "special_case": testcase["special_case"],
        "model_id": model_id,
        "provider_order": json.dumps(order, ensure_ascii=False),
        "primary_provider_slug": primary_slug,
        "primary_provider_quantization": primary_quantization,
        "actual_provider": "",
        "allow_fallbacks": str(allow_fallbacks).lower(),
        "endpoint_tools_supported": str("tools" in supported_parameters).lower(),
        "context_length": str(metadata.get("context_length") or ""),
        "max_completion_tokens": str(metadata.get("max_completion_tokens") or ""),
        "quantization": str(metadata.get("quantization") or ""),
        "openrouter_generation_id": "",
        "latency_ms": "",
        "langsmith_project": os.environ.get("LANGCHAIN_PROJECT")
        or os.environ.get("LANGSMITH_PROJECT", ""),
        "langsmith_tags": json.dumps(tags, ensure_ascii=False),
        "status": "",
        "error": "",
    }

    try:
        response = call_openrouter(
            key=key,
            model_id=model_id,
            order=order,
            allow_fallbacks=allow_fallbacks,
            system_prompt=system_prompt,
            question=testcase["query"],
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
            retry_base_seconds=args.retry_base_seconds,
            max_tokens=args.max_tokens,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = response_usage(response)
        input_cost = usage["input_tokens"] / 1_000_000 * input_price
        output_cost = usage["output_tokens"] / 1_000_000 * output_price
        generation_id = str(response.get("id") or "")
        generation = generation_details(generation_id, key)
        total_cost = compact_float(generation.get("total_cost")) or compact_float(
            input_cost + output_cost
        )
        row.update(
            {
                "answer": answer_text(response),
                "input_tokens": str(usage["input_tokens"]),
                "output_tokens": str(usage["output_tokens"]),
                "used_tokens": str(usage["used_tokens"]),
                "input_cost_usd": compact_float(input_cost),
                "output_cost_usd": compact_float(output_cost),
                "total_cost_usd": total_cost,
                "openrouter_generation_id": generation_id,
                "latency_ms": str(latency_ms),
                "actual_provider": actual_provider_slug(
                    generation,
                    primary_slug,
                    order,
                    allow_fallbacks,
                ),
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
    load_env_file(BACKEND_DIR / ".env")
    if os.environ.get("LANGSMITH_TRACING"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", os.environ["LANGSMITH_TRACING"])
    if os.environ.get("LANGSMITH_PROJECT"):
        os.environ.setdefault("LANGCHAIN_PROJECT", os.environ["LANGSMITH_PROJECT"])
    os.environ.setdefault("LANGCHAIN_CALLBACKS_BACKGROUND", "false")

    args = parse_args()
    order = provider_order(args.provider_order)
    output = args.output or (DEFAULT_FULL_OUTPUT if args.all else DEFAULT_SMOKE_OUTPUT)
    selected = parse_markdown_table(args.question_set)
    if not args.all:
        selected = selected[: args.limit]
    if args.resume:
        completed = existing_success_ids(output)
        selected = [row for row in selected if row["testcase_id"] not in completed]

    key = api_key()
    metadata = endpoint_metadata(args.model_id, order)

    print(f"model: {args.model_id}")
    print(f"provider_order: {order}")
    print(f"allow_fallbacks: {args.allow_fallbacks}")
    print(f"testcases selected: {len(selected)}")
    print(f"output: {output}")
    if metadata:
        print(
            "endpoint: "
            f"{metadata.get('provider_name')} "
            f"quant={metadata.get('quantization')} "
            f"tools={'tools' in (metadata.get('supported_parameters') or [])}"
        )
    else:
        print("endpoint: metadata not found")
    if args.dry_run:
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    mode = "a" if args.resume and output.exists() else "w"

    with output.open(mode, encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if mode == "w" or output.stat().st_size == 0:
            writer.writeheader()

        consecutive_failures = 0
        for index, testcase in enumerate(selected, start=1):
            print(f"[{index}/{len(selected)}] {testcase['testcase_id']}", flush=True)
            row = run_one(
                key=key,
                testcase=testcase,
                model_id=args.model_id,
                order=order,
                allow_fallbacks=args.allow_fallbacks,
                metadata=metadata,
                system_prompt=system_prompt,
                args=args,
            )
            writer.writerow(row)
            handle.flush()
            print(
                f"  -> {row['status']}"
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
