from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
RESULTS_DIR = ROOT_DIR / "results"
SYSTEM_PROMPT_FILE = ROOT_DIR / "src" / "prompt" / "system_prompt.j2"
DEFAULT_OUTPUT_FILE = RESULTS_DIR / "backend_settings_benchmark.csv"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def default_testcase_file() -> Path:
    candidates = [
        ROOT_DIR / "data" / "testcases" / "rag_agent_question_test_cases.md",
        ROOT_DIR / "tests" / "benchmark" / "data" / "rag_agent_question_test_cases.md",
        ROOT_DIR.parent / "docs" / "benchmark" / "data" / "rag_agent_question_test_cases.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


TESTCASE_FILE = default_testcase_file()

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

csv.field_size_limit(sys.maxsize)


def configure_env() -> None:
    load_dotenv(ROOT_DIR / ".env", override=False)

    if os.environ.get("LANGSMITH_TRACING"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", os.environ["LANGSMITH_TRACING"])
    if os.environ.get("LANGSMITH_PROJECT"):
        os.environ.setdefault("LANGCHAIN_PROJECT", os.environ["LANGSMITH_PROJECT"])
    if os.environ.get("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGCHAIN_API_KEY", os.environ["LANGSMITH_API_KEY"])

    os.environ.setdefault("LANGCHAIN_CALLBACKS_BACKGROUND", "false")


def parse_markdown_table(path: Path) -> list[dict[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("| RAG-Q-"):
            continue

        columns = [column.strip() for column in line.strip("|").split("|")]
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


def _get_json(url: str, api_key: str | None = None) -> dict[str, Any]:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _provider_slugs_by_name() -> dict[str, str]:
    data = _get_json(f"{OPENROUTER_BASE_URL}/providers")
    return {item["name"].lower(): item["slug"] for item in data["data"]}


def _price_per_1m(value: str | None) -> float:
    if not value:
        return 0.0
    return float(value) * 1_000_000


def _provider_order_primary(provider_order: list[str]) -> tuple[str, str]:
    if not provider_order:
        return "", ""

    primary = provider_order[0]
    provider_slug, _, quantization = primary.partition("/")
    return provider_slug, quantization


def fetch_endpoint_metadata(model_id: str, provider_order: list[str]) -> dict[str, Any]:
    provider_slugs = _provider_slugs_by_name()
    primary_provider_slug, primary_quantization = _provider_order_primary(provider_order)
    url = f"{OPENROUTER_BASE_URL}/models/{model_id}/endpoints"

    try:
        data = _get_json(url)
    except Exception:
        return {}

    matching_provider: list[dict[str, Any]] = []
    for endpoint in data.get("data", {}).get("endpoints", []):
        provider_slug = provider_slugs.get(str(endpoint.get("provider_name", "")).lower(), "")
        if provider_slug == primary_provider_slug:
            matching_provider.append(endpoint)

    if primary_quantization:
        for endpoint in matching_provider:
            if str(endpoint.get("quantization") or "").lower() == primary_quantization.lower():
                return endpoint

    return matching_provider[0] if matching_provider else {}


def build_llm():
    from agent.openrouter_llm import _openrouter_extra_body, _openrouter_headers
    from langchain_openai import ChatOpenAI
    from settings import settings

    if settings.openrouter_api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY or BACKEND_OPENROUTER_API_KEY is required.")

    llm_kwargs: dict[str, Any] = {
        "model": settings.openrouter_model,
        "api_key": settings.openrouter_api_key.get_secret_value(),
        "base_url": settings.openrouter_base_url,
        "temperature": settings.llm_temperature,
        "timeout": settings.llm_timeout_ms / 1000,
        "max_retries": 0,
        "default_headers": _openrouter_headers(),
        "extra_body": _openrouter_extra_body(),
    }

    if settings.llm_reasoning_effort:
        reasoning_effort = settings.llm_reasoning_effort.strip()
        if reasoning_effort.lower() not in {"none", "null", "off", "false"}:
            llm_kwargs["reasoning_effort"] = reasoning_effort
    if settings.llm_max_tokens:
        llm_kwargs["max_completion_tokens"] = settings.llm_max_tokens

    return ChatOpenAI(**llm_kwargs)


def _usage_from_response(response: Any) -> dict[str, int]:
    usage_metadata = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or {}

    input_tokens = (
        usage_metadata.get("input_tokens")
        or token_usage.get("prompt_tokens")
        or token_usage.get("input_tokens")
        or 0
    )
    output_tokens = (
        usage_metadata.get("output_tokens")
        or token_usage.get("completion_tokens")
        or token_usage.get("output_tokens")
        or 0
    )
    total_tokens = (
        usage_metadata.get("total_tokens")
        or token_usage.get("total_tokens")
        or input_tokens + output_tokens
    )

    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "used_tokens": int(total_tokens or 0),
    }


def _response_id(response: Any) -> str:
    response_metadata = getattr(response, "response_metadata", None) or {}
    response_id = response_metadata.get("id")
    if response_id:
        return str(response_id)

    message_id = getattr(response, "id", None)
    if message_id and not str(message_id).startswith("lc_run--"):
        return str(message_id)

    return ""


def fetch_generation_details(generation_id: str) -> dict[str, Any]:
    api_key = os.environ.get("BACKEND_OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not generation_id or not api_key:
        return {}

    time.sleep(0.5)
    query = urllib.parse.urlencode({"id": generation_id})
    url = f"{OPENROUTER_BASE_URL}/generation?{query}"
    try:
        data = _get_json(url, api_key=api_key)
    except Exception:
        return {}
    return data.get("data") or {}


def _float_or_empty(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.10f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def _cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_1m: float,
    output_price_per_1m: float,
) -> tuple[float, float, float]:
    input_cost = input_tokens / 1_000_000 * input_price_per_1m
    output_cost = output_tokens / 1_000_000 * output_price_per_1m
    return input_cost, output_cost, input_cost + output_cost


def _error_summary(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {str(exc)[:500]}"


def _is_retryable_rate_limit(exc: Exception) -> bool:
    text = f"{exc.__class__.__name__}: {exc}".lower()
    return (
        "ratelimiterror" in text
        or "rate-limit" in text
        or "rate-limited" in text
        or "rate_limit" in text
        or "rate limited" in text
        or "429" in text
    )


def invoke_with_rate_limit_backoff(llm: Any, messages: list[Any], config: dict[str, Any]) -> Any:
    max_attempts = int(os.environ.get("BACKEND_VALIDATION_MAX_RETRIES", "5"))
    base_sleep = float(os.environ.get("BACKEND_VALIDATION_RETRY_BASE_SECONDS", "5"))

    for attempt in range(max_attempts + 1):
        try:
            return llm.invoke(messages, config=config)
        except Exception as exc:
            if not _is_retryable_rate_limit(exc) or attempt >= max_attempts:
                raise

            sleep_seconds = min(base_sleep * (2 ** attempt), 60) + random.uniform(0, 1.5)
            print(f"  -> rate limited; sleep {sleep_seconds:.1f}s then retry {attempt + 1}/{max_attempts}", flush=True)
            time.sleep(sleep_seconds)


def fieldnames() -> list[str]:
    return [
        "timestamp",
        "testcase_id",
        "query",
        "expected_keywords",
        "reference",
        "judge_criteria",
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
        "input_price_per_1m",
        "output_price_per_1m",
        "input_tokens",
        "output_tokens",
        "used_tokens",
        "input_cost_usd",
        "output_cost_usd",
        "total_cost_usd",
        "openrouter_generation_id",
        "latency_ms",
        "langsmith_project",
        "langsmith_tags",
        "status",
        "error",
        "answer",
    ]


def existing_testcase_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()

    with path.open(encoding="utf-8-sig", newline="") as file:
        return {
            row["testcase_id"]
            for row in csv.DictReader(file)
            if row.get("status") == "success" and row.get("testcase_id")
        }


def run_one(
    *,
    llm: Any,
    system_prompt: str,
    testcase: dict[str, str],
    model_id: str,
    provider_order: list[str],
    allow_fallbacks: bool,
    endpoint_metadata: dict[str, Any],
) -> dict[str, str]:
    from langchain_core.messages import HumanMessage, SystemMessage

    started = time.perf_counter()
    pricing = endpoint_metadata.get("pricing") or {}
    supported_parameters = endpoint_metadata.get("supported_parameters") or []
    primary_provider_slug, primary_quantization = _provider_order_primary(provider_order)
    input_price_per_1m = _price_per_1m(pricing.get("prompt"))
    output_price_per_1m = _price_per_1m(pricing.get("completion"))
    tags = [
        "backend-settings-benchmark",
        model_id,
        primary_provider_slug or "provider-unspecified",
        testcase["testcase_id"],
    ]

    base_row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "testcase_id": testcase["testcase_id"],
        "query": testcase["query"],
        "expected_keywords": testcase["expected_keywords"],
        "reference": testcase["reference"],
        "judge_criteria": testcase["judge_criteria"],
        "batch": testcase["batch"],
        "difficulty": testcase["difficulty"],
        "special_case": testcase["special_case"],
        "model_id": model_id,
        "provider_order": json.dumps(provider_order, ensure_ascii=False),
        "primary_provider_slug": primary_provider_slug,
        "primary_provider_quantization": primary_quantization,
        "actual_provider": "",
        "allow_fallbacks": str(allow_fallbacks).lower(),
        "endpoint_tools_supported": str("tools" in supported_parameters).lower(),
        "context_length": str(endpoint_metadata.get("context_length") or ""),
        "max_completion_tokens": str(endpoint_metadata.get("max_completion_tokens") or ""),
        "quantization": str(endpoint_metadata.get("quantization") or ""),
        "input_price_per_1m": f"{input_price_per_1m:.8g}",
        "output_price_per_1m": f"{output_price_per_1m:.8g}",
        "input_tokens": "",
        "output_tokens": "",
        "used_tokens": "",
        "input_cost_usd": "",
        "output_cost_usd": "",
        "total_cost_usd": "",
        "openrouter_generation_id": "",
        "latency_ms": "",
        "langsmith_project": os.environ.get("LANGCHAIN_PROJECT") or os.environ.get("LANGSMITH_PROJECT", ""),
        "langsmith_tags": json.dumps(tags, ensure_ascii=False),
        "status": "",
        "error": "",
        "answer": "",
    }

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=testcase["query"]),
        ]
        response = invoke_with_rate_limit_backoff(
            llm,
            messages,
            {
                "run_name": f"backend-settings-benchmark-{testcase['testcase_id']}",
                "tags": tags,
                "metadata": {
                    "testcase_id": testcase["testcase_id"],
                    "query": testcase["query"],
                    "model_id": model_id,
                    "provider_order": provider_order,
                    "allow_fallbacks": allow_fallbacks,
                    "benchmark": "backend_settings",
                },
            },
        )

        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = _usage_from_response(response)
        input_cost, output_cost, total_cost = _cost(
            usage["input_tokens"],
            usage["output_tokens"],
            input_price_per_1m,
            output_price_per_1m,
        )
        generation_id = _response_id(response)
        generation = fetch_generation_details(generation_id)
        total_cost_from_openrouter = generation.get("total_cost")
        actual_provider = generation.get("provider_name") or ""
        if not actual_provider and (not allow_fallbacks or len(provider_order) == 1):
            actual_provider = primary_provider_slug

        base_row.update(
            {
                "actual_provider": actual_provider,
                "input_tokens": str(usage["input_tokens"]),
                "output_tokens": str(usage["output_tokens"]),
                "used_tokens": str(usage["used_tokens"]),
                "input_cost_usd": f"{input_cost:.10f}".rstrip("0").rstrip("."),
                "output_cost_usd": f"{output_cost:.10f}".rstrip("0").rstrip("."),
                "total_cost_usd": _float_or_empty(total_cost_from_openrouter)
                or f"{total_cost:.10f}".rstrip("0").rstrip("."),
                "openrouter_generation_id": generation_id,
                "latency_ms": str(latency_ms),
                "status": "success",
                "answer": str(getattr(response, "content", "")),
            }
        )
    except Exception as exc:
        base_row.update(
            {
                "latency_ms": str(int((time.perf_counter() - started) * 1000)),
                "status": "failed",
                "error": _error_summary(exc),
            }
        )

    return base_row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark testcase queries with current backend OpenRouter settings.")
    parser.add_argument("--limit", type=int, default=3, help="Number of testcases to run unless --all is set.")
    parser.add_argument("--all", action="store_true", help="Run all parsed testcases.")
    parser.add_argument("--resume", action="store_true", help="Skip successful testcase rows already present in output.")
    parser.add_argument("--dry-run", action="store_true", help="Print selected settings and run count without LLM calls.")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=float(os.environ.get("BACKEND_VALIDATION_SLEEP_SECONDS", "0")),
        help="Seconds to sleep between successful or failed testcase calls.",
    )
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based shard index.")
    parser.add_argument("--shard-count", type=int, default=1, help="Total shard count.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    return parser.parse_args()


def main() -> None:
    configure_env()

    from settings import settings

    args = parse_args()
    if args.shard_count < 1:
        raise ValueError("--shard-count must be >= 1")
    if args.shard_index < 0 or args.shard_index >= args.shard_count:
        raise ValueError("--shard-index must be between 0 and shard-count - 1")

    testcases = parse_markdown_table(TESTCASE_FILE)
    if not args.all:
        testcases = testcases[: args.limit]
    if args.shard_count > 1:
        testcases = [
            testcase
            for index, testcase in enumerate(testcases)
            if index % args.shard_count == args.shard_index
        ]

    output_file = args.output
    existing_ids = existing_testcase_ids(output_file) if args.resume else set()
    selected_testcases = [row for row in testcases if row["testcase_id"] not in existing_ids]
    endpoint_metadata = fetch_endpoint_metadata(settings.openrouter_model, settings.openrouter_provider_order)

    print(f"model: {settings.openrouter_model}")
    print(f"provider_order: {settings.openrouter_provider_order}")
    print(f"allow_fallbacks: {settings.openrouter_allow_fallbacks}")
    print(f"max_tokens: {settings.llm_max_tokens or ''}")
    print(f"reasoning_effort: {settings.llm_reasoning_effort or ''}")
    print(f"langsmith_project: {os.environ.get('LANGCHAIN_PROJECT') or os.environ.get('LANGSMITH_PROJECT', '')}")
    print(f"testcases selected: {len(selected_testcases)} / {len(testcases)}")
    print(f"shard: {args.shard_index + 1}/{args.shard_count}")
    print(f"sleep_seconds: {args.sleep_seconds}")
    stop_after_failures = int(os.environ.get("BACKEND_VALIDATION_STOP_AFTER_FAILURES", "0"))
    print(f"stop_after_failures: {stop_after_failures}")
    print(f"output: {output_file}")
    if endpoint_metadata:
        print(
            "endpoint: "
            f"{endpoint_metadata.get('provider_name')} "
            f"quant={endpoint_metadata.get('quantization')} "
            f"tools={'tools' in (endpoint_metadata.get('supported_parameters') or [])}"
        )
    else:
        print("endpoint: metadata not found")

    if args.dry_run:
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    llm = build_llm()

    file_exists = output_file.exists()
    mode = "a" if args.resume and file_exists else "w"
    with output_file.open(mode, encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames())
        if mode == "w" or output_file.stat().st_size == 0:
            writer.writeheader()

        consecutive_failures = 0
        for index, testcase in enumerate(selected_testcases, start=1):
            print(f"[{index}/{len(selected_testcases)}] {testcase['testcase_id']}", flush=True)
            row = run_one(
                llm=llm,
                system_prompt=system_prompt,
                testcase=testcase,
                model_id=settings.openrouter_model,
                provider_order=settings.openrouter_provider_order,
                allow_fallbacks=settings.openrouter_allow_fallbacks,
                endpoint_metadata=endpoint_metadata,
            )
            writer.writerow(row)
            file.flush()
            print(f"  -> {row['status']}" + (f": {row['error']}" if row["error"] else ""), flush=True)
            if row["status"] == "failed":
                consecutive_failures += 1
            else:
                consecutive_failures = 0
            if stop_after_failures > 0 and consecutive_failures >= stop_after_failures:
                print(
                    f"stopping after {consecutive_failures} consecutive failures",
                    flush=True,
                )
                break
            if args.sleep_seconds > 0 and index < len(selected_testcases):
                time.sleep(args.sleep_seconds)

    print(f"wrote CSV: {output_file}")


if __name__ == "__main__":
    main()
