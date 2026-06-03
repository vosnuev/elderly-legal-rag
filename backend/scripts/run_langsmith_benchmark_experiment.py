from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from langsmith import Client

from langsmith_benchmark_common import (
    DEFAULT_DATASET_NAME,
    SRC_DIR,
    SYSTEM_PROMPT_FILE,
    configure_env,
    parse_markdown_table,
    required_keywords,
)
from run_backend_settings_benchmark import (
    _cost,
    _float_or_empty,
    _price_per_1m,
    _provider_order_primary,
    _response_id,
    _usage_from_response,
    build_llm,
    fetch_endpoint_metadata,
    fetch_generation_details,
    invoke_with_rate_limit_backoff,
)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the benchmark as a LangSmith dataset experiment.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--experiment-prefix", default="")
    parser.add_argument("--description", default="SKN28 backend settings benchmark via LangSmith evaluate().")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="")
    parser.add_argument("--provider-order", default="", help="Comma-separated provider order, e.g. deepseek or gmicloud")
    parser.add_argument("--allow-fallbacks", choices=["true", "false"], default="")
    parser.add_argument("--reasoning-effort", default="")
    return parser.parse_args()


def apply_overrides(args: argparse.Namespace) -> None:
    if args.model:
        os.environ["BACKEND_OPENROUTER_MODEL"] = args.model
    if args.provider_order:
        providers = [item.strip() for item in args.provider_order.split(",") if item.strip()]
        os.environ["BACKEND_OPENROUTER_PROVIDER_ORDER"] = json.dumps(providers)
    if args.allow_fallbacks:
        os.environ["BACKEND_OPENROUTER_ALLOW_FALLBACKS"] = args.allow_fallbacks
    if args.reasoning_effort:
        os.environ["BACKEND_LLM_REASONING_EFFORT"] = args.reasoning_effort


def example_sort_key(example: Any) -> str:
    metadata = getattr(example, "metadata", None) or {}
    inputs = getattr(example, "inputs", None) or {}
    return str(metadata.get("testcase_id") or inputs.get("testcase_id") or "")


def keyword_coverage_evaluator(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    answer = str(outputs.get("answer") or "")
    keywords = required_keywords(str(reference_outputs.get("expected_keywords") or ""))
    if not keywords:
        return {"key": "required_keyword_coverage", "score": None, "comment": "No required keywords parsed."}

    missing = [keyword for keyword in keywords if keyword not in answer]
    score = (len(keywords) - len(missing)) / len(keywords)
    comment = "All required keywords present." if not missing else f"Missing: {', '.join(missing)}"
    return {"key": "required_keyword_coverage", "score": score, "comment": comment}


def success_status_evaluator(inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    status = outputs.get("status")
    return {
        "key": "success_status",
        "score": status == "success",
        "comment": str(outputs.get("error") or "success"),
    }


def build_target() -> Any:
    from langchain_core.messages import HumanMessage, SystemMessage
    from settings import settings

    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    llm = build_llm()
    endpoint_metadata = fetch_endpoint_metadata(settings.openrouter_model, settings.openrouter_provider_order)
    pricing = endpoint_metadata.get("pricing") or {}
    supported_parameters = endpoint_metadata.get("supported_parameters") or []
    primary_provider_slug, primary_quantization = _provider_order_primary(settings.openrouter_provider_order)
    input_price_per_1m = _price_per_1m(pricing.get("prompt"))
    output_price_per_1m = _price_per_1m(pricing.get("completion"))

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        testcase_id = str(inputs["testcase_id"])
        query = str(inputs["query"])
        started = time.perf_counter()
        tags = [
            "backend-settings-benchmark",
            "langsmith-experiment",
            settings.openrouter_model,
            primary_provider_slug or "provider-unspecified",
            testcase_id,
        ]
        try:
            response = invoke_with_rate_limit_backoff(
                llm,
                [SystemMessage(content=system_prompt), HumanMessage(content=query)],
                {
                    "run_name": f"backend-settings-benchmark-{testcase_id}",
                    "tags": tags,
                    "metadata": {
                        "benchmark": "backend_settings",
                        "testcase_id": testcase_id,
                        "query": query,
                        "model_id": settings.openrouter_model,
                        "provider_order": settings.openrouter_provider_order,
                        "allow_fallbacks": settings.openrouter_allow_fallbacks,
                    },
                },
            )
        except Exception as exc:
            return {
                "answer": "",
                "status": "error",
                "error": f"{exc.__class__.__name__}: {str(exc)[:500]}",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "model_id": settings.openrouter_model,
                "provider_order": settings.openrouter_provider_order,
                "primary_provider_slug": primary_provider_slug,
            }

        usage = _usage_from_response(response)
        input_cost, output_cost, total_cost = _cost(
            usage["input_tokens"],
            usage["output_tokens"],
            input_price_per_1m,
            output_price_per_1m,
        )
        generation_id = _response_id(response)
        generation = fetch_generation_details(generation_id)
        actual_provider = generation.get("provider_name") or primary_provider_slug
        total_cost_from_openrouter = generation.get("total_cost")

        return {
            "answer": str(getattr(response, "content", "")),
            "status": "success",
            "error": "",
            "model_id": settings.openrouter_model,
            "provider_order": settings.openrouter_provider_order,
            "primary_provider_slug": primary_provider_slug,
            "primary_provider_quantization": primary_quantization,
            "actual_provider": actual_provider,
            "allow_fallbacks": settings.openrouter_allow_fallbacks,
            "endpoint_tools_supported": "tools" in supported_parameters,
            "context_length": endpoint_metadata.get("context_length") or "",
            "max_completion_tokens": endpoint_metadata.get("max_completion_tokens") or "",
            "quantization": endpoint_metadata.get("quantization") or "",
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "used_tokens": usage["used_tokens"],
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": _float_or_empty(total_cost_from_openrouter) or total_cost,
            "openrouter_generation_id": generation_id,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }

    return target


def main() -> None:
    args = parse_args()
    configure_env()
    apply_overrides(args)

    from settings import settings

    client = Client()
    try:
        dataset = client.read_dataset(dataset_name=args.dataset)
        dataset_exists = True
    except Exception:
        dataset = None
        dataset_exists = False

    if dataset is None:
        if not args.dry_run:
            raise SystemExit(
                f"Dataset not found: {args.dataset}. "
                "Run sync_langsmith_benchmark_dataset.py first."
            )
        local_count = len(parse_markdown_table())
        examples = []
        selected_count = min(local_count, args.limit) if args.limit else local_count
    else:
        examples = sorted(client.list_examples(dataset_id=dataset.id, limit=10_000), key=example_sort_key)
        if args.limit:
            examples = examples[: args.limit]
        selected_count = len(examples)

    primary_provider_slug, _ = _provider_order_primary(settings.openrouter_provider_order)
    experiment_prefix = args.experiment_prefix or (
        f"{settings.openrouter_model.replace('/', '__')}__{primary_provider_slug or 'provider-unspecified'}"
    )

    print(f"dataset: {args.dataset}")
    print(f"dataset_exists: {dataset_exists}")
    if dataset is not None:
        print(f"dataset_id: {dataset.id}")
        print(f"examples: {selected_count} / {dataset.example_count}")
    else:
        print(f"examples: {selected_count} / local_testcases")
    print(f"model: {settings.openrouter_model}")
    print(f"provider_order: {settings.openrouter_provider_order}")
    print(f"allow_fallbacks: {settings.openrouter_allow_fallbacks}")
    print(f"experiment_prefix: {experiment_prefix}")
    print(f"max_concurrency: {args.max_concurrency}")

    if args.dry_run:
        return

    results = client.evaluate(
        build_target(),
        data=examples,
        evaluators=[keyword_coverage_evaluator, success_status_evaluator],
        experiment_prefix=experiment_prefix,
        description=args.description,
        max_concurrency=args.max_concurrency,
        metadata={
            "benchmark": "backend_settings",
            "model_id": settings.openrouter_model,
            "provider_order": settings.openrouter_provider_order,
            "allow_fallbacks": settings.openrouter_allow_fallbacks,
        },
        error_handling="log",
    )
    print(f"experiment: {results.experiment_name}")


if __name__ == "__main__":
    main()
