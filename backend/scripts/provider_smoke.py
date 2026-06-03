from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
RESULT_FILE = RESULTS_DIR / "provider_smoke_results.csv"
VALIDATION_SMOKE_SCRIPT = ROOT_DIR / "scripts" / "validation_smoke.py"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_PROVIDERS_URL = "https://openrouter.ai/api/v1/providers"

MODELS = [
    {
        "label": "MiniMax M3",
        "model_id": "minimax/minimax-m3",
        "endpoints_model_id": "minimax/minimax-m3-20260531",
    },
    {
        "label": "Qwen 3.7 Max",
        "model_id": "qwen/qwen3.7-max",
        "endpoints_model_id": "qwen/qwen3.7-max",
    },
    {
        "label": "DeepSeek V4 Pro",
        "model_id": "deepseek/deepseek-v4-pro",
        "endpoints_model_id": "deepseek/deepseek-v4-pro",
    },
    {
        "label": "DeepSeek V4 Flash",
        "model_id": "deepseek/deepseek-v4-flash",
        "endpoints_model_id": "deepseek/deepseek-v4-flash",
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
    provider_name: str
    provider_slug: str
    context_length: int | None
    max_completion_tokens: int | None
    quantization: str | None
    supports_tools: bool
    input_price_per_1m: float
    output_price_per_1m: float


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
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
            pricing = endpoint.get("pricing") or {}
            supported_parameters = endpoint.get("supported_parameters") or []

            targets.append(
                ProviderTarget(
                    model_label=model["label"],
                    model_id=model["model_id"],
                    provider_name=provider_name,
                    provider_slug=provider_slugs.get(provider_name.lower(), ""),
                    context_length=endpoint.get("context_length"),
                    max_completion_tokens=endpoint.get("max_completion_tokens"),
                    quantization=endpoint.get("quantization"),
                    supports_tools="tools" in supported_parameters,
                    input_price_per_1m=_price_per_1m(pricing.get("prompt")),
                    output_price_per_1m=_price_per_1m(pricing.get("completion")),
                )
            )

    return [
        target
        for target in targets
        if target.provider_slug in RECOMMENDED_PROVIDER_SLUGS[target.model_id]
    ]


def _error_summary(stdout: str, stderr: str) -> str:
    text = "\n".join(part for part in [stderr.strip(), stdout.strip()] if part)
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if "Error code:" in line or "RateLimitError" in line or "BadRequestError" in line:
            return line[:500]
    return lines[-1][:500]


def run_target(target: ProviderTarget) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src:scripts"
    env["BACKEND_OPENROUTER_MODEL"] = target.model_id
    env["BACKEND_OPENROUTER_PROVIDER_ORDER"] = json.dumps([target.provider_slug])
    env["BACKEND_OPENROUTER_ALLOW_FALLBACKS"] = "false"

    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(VALIDATION_SMOKE_SCRIPT)],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    status = "success" if completed.returncode == 0 else "failed"
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_label": target.model_label,
        "model_id": target.model_id,
        "provider_name": target.provider_name,
        "provider_slug": target.provider_slug,
        "tool_mode": "no_tool",
        "allow_fallbacks": "false",
        "endpoint_tools_supported": str(target.supports_tools).lower(),
        "context_length": str(target.context_length or ""),
        "max_completion_tokens": str(target.max_completion_tokens or ""),
        "quantization": target.quantization or "",
        "input_price_per_1m": f"{target.input_price_per_1m:.8g}",
        "output_price_per_1m": f"{target.output_price_per_1m:.8g}",
        "status": status,
        "return_code": str(completed.returncode),
        "latency_ms": str(latency_ms),
        "error": "" if status == "success" else _error_summary(completed.stdout, completed.stderr),
    }


def write_results(rows: list[dict[str, str]]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp",
        "model_label",
        "model_id",
        "provider_name",
        "provider_slug",
        "tool_mode",
        "allow_fallbacks",
        "endpoint_tools_supported",
        "context_length",
        "max_completion_tokens",
        "quantization",
        "input_price_per_1m",
        "output_price_per_1m",
        "status",
        "return_code",
        "latency_ms",
        "error",
    ]

    with RESULT_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    load_dotenv(ROOT_DIR / ".env", override=False)

    targets = fetch_provider_targets()
    print(f"provider smoke targets: {len(targets)}")
    print(f"result file: {RESULT_FILE}")

    rows: list[dict[str, str]] = []
    for index, target in enumerate(targets, start=1):
        print(
            f"[{index}/{len(targets)}] "
            f"{target.model_id} / {target.provider_slug} "
            f"(tools={target.supports_tools})",
            flush=True,
        )
        row = run_target(target)
        rows.append(row)
        print(f"  -> {row['status']}" + (f": {row['error']}" if row["error"] else ""), flush=True)

    write_results(rows)
    print(f"\nwrote {len(rows)} rows to {RESULT_FILE}")


if __name__ == "__main__":
    main()
