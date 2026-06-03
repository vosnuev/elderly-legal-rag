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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
DEFAULT_OUTPUT_FILE = RESULTS_DIR / "llm_validation_results.csv"
PROVIDER_SMOKE_FILE = RESULTS_DIR / "provider_smoke_results.csv"
TESTCASE_FILE = ROOT_DIR / "data" / "testcases" / "rag_agent_question_test_cases.md"
SYSTEM_PROMPT_FILE = ROOT_DIR / "src" / "prompt" / "system_prompt.j2"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS_URL = f"{OPENROUTER_BASE_URL}/models"
OPENROUTER_PROVIDERS_URL = f"{OPENROUTER_BASE_URL}/providers"

csv.field_size_limit(sys.maxsize)

MODELS = [
    {
        "label": "MiniMax M3",
        "model_id": "minimax/minimax-m3",
        "endpoints_model_id": "minimax/minimax-m3-20260531",
        "sheet_name": "minimax_m3",
    },
    {
        "label": "Qwen 3.7 Max",
        "model_id": "qwen/qwen3.7-max",
        "endpoints_model_id": "qwen/qwen3.7-max",
        "sheet_name": "qwen_3_7_max",
    },
    {
        "label": "DeepSeek V4 Pro",
        "model_id": "deepseek/deepseek-v4-pro",
        "endpoints_model_id": "deepseek/deepseek-v4-pro",
        "sheet_name": "deepseek_v4_pro",
    },
    {
        "label": "DeepSeek V4 Flash",
        "model_id": "deepseek/deepseek-v4-flash",
        "endpoints_model_id": "deepseek/deepseek-v4-flash",
        "sheet_name": "deepseek_v4_flash",
    },
]

RECOMMENDED_PROVIDER_SLUGS = {
    "minimax/minimax-m3": {"minimax"},
    "qwen/qwen3.7-max": {"alibaba"},
    "deepseek/deepseek-v4-pro": {
        "deepseek",
        "gmicloud",
        "streamlake",
        "novita",
        "siliconflow",
        "alibaba",
        "atlas-cloud",
    },
    "deepseek/deepseek-v4-flash": {
        "baidu",
        "deepinfra",
        "gmicloud",
        "streamlake",
        "siliconflow",
        "alibaba",
        "deepseek",
        "parasail",
        "atlas-cloud",
        "akashml",
        "novita",
    },
}


@dataclass(frozen=True)
class ProviderTarget:
    model_label: str
    model_id: str
    sheet_name: str
    provider_name: str
    provider_slug: str
    context_length: int | None
    max_completion_tokens: int | None
    quantization: str | None
    supports_tools: bool
    input_price_per_1m: float
    output_price_per_1m: float


def configure_langsmith_env() -> None:
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
    data = _get_json(OPENROUTER_PROVIDERS_URL)
    return {item["name"].lower(): item["slug"] for item in data["data"]}


def _price_per_1m(value: str | None) -> float:
    if not value:
        return 0.0
    return float(value) * 1_000_000


def fetch_provider_targets() -> list[ProviderTarget]:
    provider_slugs = _provider_slugs_by_name()
    targets: list[ProviderTarget] = []

    for model in MODELS:
        endpoint_url = (
            f"{OPENROUTER_MODELS_URL}/"
            f"{model['endpoints_model_id']}/endpoints"
        )
        data = _get_json(endpoint_url)

        for endpoint in data["data"]["endpoints"]:
            provider_name = endpoint["provider_name"]
            provider_slug = provider_slugs.get(provider_name.lower(), "")
            if provider_slug not in RECOMMENDED_PROVIDER_SLUGS[model["model_id"]]:
                continue

            pricing = endpoint.get("pricing") or {}
            supported_parameters = endpoint.get("supported_parameters") or []
            targets.append(
                ProviderTarget(
                    model_label=model["label"],
                    model_id=model["model_id"],
                    sheet_name=model["sheet_name"],
                    provider_name=provider_name,
                    provider_slug=provider_slug,
                    context_length=endpoint.get("context_length"),
                    max_completion_tokens=endpoint.get("max_completion_tokens"),
                    quantization=endpoint.get("quantization"),
                    supports_tools="tools" in supported_parameters,
                    input_price_per_1m=_price_per_1m(pricing.get("prompt")),
                    output_price_per_1m=_price_per_1m(pricing.get("completion")),
                )
            )

    return targets


def successful_smoke_pairs() -> set[tuple[str, str]]:
    if not PROVIDER_SMOKE_FILE.exists():
        return set()

    pairs: set[tuple[str, str]] = set()
    with PROVIDER_SMOKE_FILE.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("status") == "success":
                pairs.add((row["model_id"], row["provider_slug"]))
    return pairs


def build_llm(target: ProviderTarget):
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("BACKEND_OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("BACKEND_OPENROUTER_API_KEY or OPENROUTER_API_KEY is required.")

    return ChatOpenAI(
        model=target.model_id,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        temperature=float(os.environ.get("BACKEND_LLM_TEMPERATURE", "0.2")),
        timeout=int(os.environ.get("BACKEND_LLM_TIMEOUT_MS", "60000")) / 1000,
        max_retries=0,
        default_headers={
            "X-Title": os.environ.get("BACKEND_OPENROUTER_APP_TITLE", "SKN28 Backend Validation"),
        },
        extra_body={
            "provider": {
                "order": [target.provider_slug],
                "allow_fallbacks": False,
                "data_collection": "deny",
            }
        },
    )


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


def _cost(input_tokens: int, output_tokens: int, target: ProviderTarget) -> tuple[float, float, float]:
    input_cost = input_tokens / 1_000_000 * target.input_price_per_1m
    output_cost = output_tokens / 1_000_000 * target.output_price_per_1m
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
            print(f" -> rate limited; sleep {sleep_seconds:.1f}s then retry {attempt + 1}/{max_attempts}", flush=True)
            time.sleep(sleep_seconds)


def run_one(
    llm: Any,
    system_prompt: str,
    testcase: dict[str, str],
    target: ProviderTarget,
    tool_mode: str,
) -> dict[str, str]:
    from langchain_core.messages import HumanMessage, SystemMessage

    started = time.perf_counter()
    base_row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "testcase_id": testcase["testcase_id"],
        "query": testcase["query"],
        "expected_keywords": testcase["expected_keywords"],
        "reference": testcase["reference"],
        "batch": testcase["batch"],
        "difficulty": testcase["difficulty"],
        "special_case": testcase["special_case"],
        "model_label": target.model_label,
        "model_id": target.model_id,
        "sheet_name": target.sheet_name,
        "provider_name": target.provider_name,
        "provider_slug": target.provider_slug,
        "provider_order": json.dumps([target.provider_slug], ensure_ascii=False),
        "actual_provider": "",
        "allow_fallbacks": "false",
        "tool_mode": tool_mode,
        "endpoint_tools_supported": str(target.supports_tools).lower(),
        "context_length": str(target.context_length or ""),
        "max_completion_tokens": str(target.max_completion_tokens or ""),
        "quantization": target.quantization or "",
        "input_price_per_1m": f"{target.input_price_per_1m:.8g}",
        "output_price_per_1m": f"{target.output_price_per_1m:.8g}",
        "input_tokens": "",
        "output_tokens": "",
        "used_tokens": "",
        "input_cost_usd": "",
        "output_cost_usd": "",
        "total_cost_usd": "",
        "openrouter_generation_id": "",
        "langsmith_run_id": "",
        "latency_ms": "",
        "status": "",
        "error": "",
        "answer": "",
    }

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=testcase["query"]),
        ]
        config = {
            "tags": [
                "llm-validation",
                tool_mode,
                target.model_id,
                target.provider_slug,
                testcase["testcase_id"],
            ],
            "metadata": {
                "testcase_id": testcase["testcase_id"],
                "model_id": target.model_id,
                "provider_slug": target.provider_slug,
                "tool_mode": tool_mode,
            },
        }
            
        response = invoke_with_rate_limit_backoff(llm, messages, config)
        
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = _usage_from_response(response)
        input_cost, output_cost, total_cost = _cost(
            usage["input_tokens"],
            usage["output_tokens"],
            target,
        )
        generation_id = _response_id(response)
        generation = fetch_generation_details(generation_id)
        total_cost_from_openrouter = generation.get("total_cost")

        base_row.update(
            {
                "actual_provider": generation.get("provider_name") or target.provider_name,
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
        latency_ms = int((time.perf_counter() - started) * 1000)
        base_row.update(
            {
                "latency_ms": str(latency_ms),
                "status": "failed",
                "error": _error_summary(exc),
            }
        )

    return base_row


def fieldnames() -> list[str]:
    return [
        "timestamp",
        "testcase_id",
        "query",
        "expected_keywords",
        "reference",
        "batch",
        "difficulty",
        "special_case",
        "model_label",
        "model_id",
        "sheet_name",
        "provider_name",
        "provider_slug",
        "provider_order",
        "actual_provider",
        "allow_fallbacks",
        "tool_mode",
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
        "langsmith_run_id",
        "latency_ms",
        "status",
        "error",
        "answer",
    ]


def row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("model_id", ""),
        row.get("provider_slug", ""),
        row.get("tool_mode", ""),
        row.get("testcase_id", ""),
    )


def existing_run_keys(path: Path) -> set[tuple[str, str, str, str]]:
    if not path.exists():
        return set()

    with path.open(encoding="utf-8-sig", newline="") as file:
        return {row_key(row) for row in csv.DictReader(file)}


def existing_failed_pairs(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()

    failed_pairs: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("status") != "success":
                failed_pairs.add((row.get("model_id", ""), row.get("provider_slug", "")))
    return failed_pairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM validation and write CSV results.")
    parser.add_argument("--limit", type=int, default=3, help="Number of testcases per provider.")
    parser.add_argument("--all", action="store_true", help="Run all 360 testcases.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Append only missing model/provider/tool/testcase rows when output already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected run count without calling LLMs.",
    )
    parser.add_argument(
        "--skip-existing-failed-pairs",
        action="store_true",
        help="Skip model/provider pairs that already have failed rows in the output CSV.",
    )
    parser.add_argument("--model-id", action="append", help="Filter by model id. Repeatable.")
    parser.add_argument("--provider", action="append", help="Filter by provider slug. Repeatable.")
    parser.add_argument(
        "--successful-smoke-only",
        action="store_true",
        help="Only run model/provider pairs that succeeded in provider_smoke_results.csv.",
    )
    return parser.parse_args()


def main() -> None:
    configure_langsmith_env()
    args = parse_args()

    testcases = parse_markdown_table(TESTCASE_FILE)
    if not args.all:
        testcases = testcases[: args.limit]

    targets = fetch_provider_targets()
    if args.model_id:
        model_ids = set(args.model_id)
        targets = [target for target in targets if target.model_id in model_ids]
    if args.provider:
        providers = set(args.provider)
        targets = [target for target in targets if target.provider_slug in providers]
    if args.successful_smoke_only:
        pairs = successful_smoke_pairs()
        targets = [target for target in targets if (target.model_id, target.provider_slug) in pairs]
    if args.skip_existing_failed_pairs:
        failed_pairs = existing_failed_pairs(args.output)
        targets = [
            target
            for target in targets
            if (target.model_id, target.provider_slug) not in failed_pairs
        ]

    if not targets:
        raise RuntimeError("No provider targets selected.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    existing_keys = existing_run_keys(output_file) if args.resume else set()
    selected_runs = [
        (target, testcase)
        for target in targets
        for testcase in testcases
        if (
            target.model_id,
            target.provider_slug,
            "no_tool",
            testcase["testcase_id"],
        )
        not in existing_keys
    ]
    total_possible_runs = len(targets) * len(testcases)
    total_runs = len(selected_runs)

    print(f"targets: {len(targets)}")
    print(f"testcases per target: {len(testcases)}")
    print(f"total possible runs: {total_possible_runs}")
    print(f"existing rows skipped: {total_possible_runs - total_runs}")
    print(f"runs to execute: {total_runs}")
    print(f"output: {output_file}")

    if args.dry_run:
        return

    file_exists = output_file.exists()
    mode = "a" if args.resume and file_exists else "w"
    with output_file.open(mode, encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames())
        if mode == "w" or output_file.stat().st_size == 0:
            writer.writeheader()

        run_index = 0
        current_llm_key: tuple[str, str] | None = None
        llm = None
        for target, testcase in selected_runs:
            llm_key = (target.model_id, target.provider_slug)
            if current_llm_key != llm_key:
                llm = build_llm(target)
                current_llm_key = llm_key

            if llm is None:
                raise RuntimeError("LLM was not initialized.")

            run_index += 1
            print(
                f"[{run_index}/{total_runs}] "
                f"{target.model_id} / {target.provider_slug} / {testcase['testcase_id']}",
                flush=True,
            )
            row = run_one(
                llm=llm,
                system_prompt=system_prompt,
                testcase=testcase,
                target=target,
                tool_mode="no_tool",
            )
            writer.writerow(row)
            file.flush()
            print(f"  -> {row['status']}" + (f": {row['error']}" if row["error"] else ""), flush=True)

    print(f"\nwrote CSV: {output_file}")


if __name__ == "__main__":
    main()
