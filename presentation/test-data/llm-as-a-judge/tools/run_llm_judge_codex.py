from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


JUDGE_DIR = Path(__file__).resolve().parents[1]
TEST_DATA_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[4]
NO_TOOL_BENCHMARK_DIR = TEST_DATA_DIR / "no-tool-benchmark"
RAW_RESULTS_DIR = NO_TOOL_BENCHMARK_DIR / "raw-results"
QUESTION_SET_PATH = (
    TEST_DATA_DIR / "rag-agent-question-cases" / "rag_agent_question_test_cases_360.md"
)
OUTPUT_DIR = JUDGE_DIR / "artifacts" / "tools-no"
OUTPUT_CSV = OUTPUT_DIR / "llm_judge_results.csv"
CHECKPOINT_JSONL = OUTPUT_DIR / "llm_judge_results.checkpoint.jsonl"
WEB_CACHE_JSON = OUTPUT_DIR / "llm_judge_web_cache.json"
SCHEMA_PATH = Path(__file__).resolve().with_name("llm_judge_output_schema.json")

SELECTED_FILES = [
    "openai_gpt_oss_120b_cerebras_fp16.csv",
    "deepseek_v4_flash_deepseek.csv",
    "deepseek_v4_pro_deepseek.csv",
    "qwen_qwen3_7_plus_alibaba.csv",
]

OUTPUT_COLUMNS = [
    "question_number",
    "question",
    "source_file",
    "model_id",
    "provider",
    "actual_provider",
    "status",
    "llm_answer",
    "input_tokens",
    "output_tokens",
    "used_tokens",
    "total_cost_usd",
    "latency_ms",
    "judge_result",
    "judge_reason",
    "web_check",
    "source_urls",
]
VALID_JUDGE_RESULTS = {"correct", "wrong"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a web-enabled Codex LLM judge over selected no-tool CSV rows."
    )
    parser.add_argument("--raw-results-dir", type=Path, default=RAW_RESULTS_DIR)
    parser.add_argument("--question-set", type=Path, default=QUESTION_SET_PATH)
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--checkpoint-jsonl", type=Path, default=CHECKPOINT_JSONL)
    parser.add_argument("--web-cache-json", type=Path, default=WEB_CACHE_JSON)
    parser.add_argument("--chunk-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--model", default="gpt-5.3-codex-spark")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--skip-web-search", action="store_true")
    parser.add_argument("--codex-search", action="store_true")
    parser.add_argument("--use-output-schema", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def parse_markdown_table(path: Path) -> dict[str, dict[str, str]]:
    questions: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| RAG-Q-"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 8:
            raise ValueError(f"Unexpected table row shape in {path}: {line[:160]}")
        (
            testcase_id,
            question,
            keyword_answer,
            reference,
            judge_criteria,
            batch,
            difficulty,
            special_case,
        ) = parts
        questions[testcase_id] = {
            "question": question,
            "keyword_answer": keyword_answer,
            "reference": reference,
            "judge_criteria": judge_criteria,
            "batch": batch,
            "difficulty": difficulty,
            "special_case": special_case,
        }
    return questions


def parse_query_reference(value: str) -> dict[str, str]:
    prefixes = {
        "query": "query: ",
        "expected_keywords": "expected_keywords: ",
        "reference": "reference: ",
        "judge_criteria": "judge_criteria: ",
    }
    parsed: dict[str, str] = {}
    key: str | None = None
    buffer: list[str] = []
    for line in value.splitlines():
        matched = False
        for candidate, prefix in prefixes.items():
            if line.startswith(prefix):
                if key is not None:
                    parsed[key] = "\n".join(buffer).strip()
                key = candidate
                buffer = [line.removeprefix(prefix).strip()]
                matched = True
                break
        if not matched and key is not None:
            buffer.append(line)
    if key is not None:
        parsed[key] = "\n".join(buffer).strip()
    return parsed


def load_benchmark_rows(
    raw_results_dir: Path, questions: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for file_name in SELECTED_FILES:
        path = raw_results_dir / file_name
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                testcase_id = row["testcase_id"]
                query_reference = parse_query_reference(row.get("query_reference", ""))
                question_row = questions[testcase_id]
                if query_reference.get("query") != question_row["question"]:
                    raise ValueError(f"Question mismatch for {file_name} {testcase_id}")
                row_id = f"{file_name}::{testcase_id}"
                rows.append(
                    {
                        "row_id": row_id,
                        "question_number": testcase_id,
                        "question": question_row["question"],
                        "source_file": file_name,
                        "model_id": row.get("model_id", ""),
                        "provider": row.get("primary_provider_slug", ""),
                        "actual_provider": row.get("actual_provider", ""),
                        "status": row.get("status", ""),
                        "llm_answer": row.get("answer", ""),
                        "input_tokens": row.get("input_tokens", ""),
                        "output_tokens": row.get("output_tokens", ""),
                        "used_tokens": row.get("used_tokens", ""),
                        "total_cost_usd": row.get("total_cost_usd", ""),
                        "latency_ms": row.get("latency_ms", ""),
                        "_keyword_answer": question_row["keyword_answer"],
                        "_reference": question_row["reference"],
                        "_judge_criteria": question_row["judge_criteria"],
                        "_batch": question_row["batch"],
                        "_difficulty": question_row["difficulty"],
                        "_special_case": question_row["special_case"],
                    }
                )
    return rows


def load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    results: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item.get("judge_result") not in VALID_JUDGE_RESULTS:
                continue
            results[item["row_id"]] = item
    return results


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_object(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def keyword_query_text(keyword_answer: str) -> str:
    match = re.search(r"필수 키워드:\s*([^.]*)", keyword_answer)
    if match:
        return match.group(1).strip()
    return keyword_answer[:120]


def reference_query_text(reference: str) -> str:
    names = re.findall(r"cleaned_[^.;\s]+", reference)
    if names:
        return " ".join(names[:3])
    return reference[:120]


def make_search_query(item: dict[str, str]) -> str:
    parts = [
        item["question"],
        keyword_query_text(item["_keyword_answer"]),
        reference_query_text(item["_reference"]),
    ]
    return " ".join(part for part in parts if part).strip()[:450]


def firecrawl_search(query: str) -> dict[str, Any]:
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return {"query": query, "results": [], "error": "FIRECRAWL_API_KEY not set"}

    payload = json.dumps(
        {
            "query": query,
            "limit": 3,
            "sources": [{"type": "web"}],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.firecrawl.dev/v2/search",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        return {"query": query, "results": [], "error": str(exc)}

    web_results = data.get("data", {}).get("web", []) if data.get("success") else []
    return {
        "query": query,
        "results": [
            {
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "description": result.get("description", ""),
            }
            for result in web_results[:3]
        ],
        "search_id": data.get("id", ""),
        "credits_used": data.get("creditsUsed", ""),
        "error": "" if data.get("success") else str(data),
    }


def ensure_web_cache(
    rows: list[dict[str, str]], cache_path: Path, skip_web_search: bool
) -> dict[str, Any]:
    cache = load_json_object(cache_path)
    if skip_web_search:
        return cache

    unique_by_question: dict[str, dict[str, str]] = {}
    for row in rows:
        unique_by_question.setdefault(row["question_number"], row)

    missing = [
        item
        for question_number, item in unique_by_question.items()
        if question_number not in cache
    ]
    for index, item in enumerate(missing, start=1):
        query = make_search_query(item)
        print(
            f"Web search {index}/{len(missing)}: "
            f"{item['question_number']} {query[:90]}",
            flush=True,
        )
        cache[item["question_number"]] = firecrawl_search(query)
        save_json_object(cache_path, cache)
    return cache


def make_prompt(chunk: list[dict[str, str]]) -> str:
    prompt_items = []
    for item in chunk:
        prompt_items.append(
            {
                "row_id": item["row_id"],
                "question": item["question"],
                "benchmark_metadata": {
                    "batch": item["_batch"],
                    "difficulty": item["_difficulty"],
                    "special_case": item["_special_case"],
                },
                "private_judge_reference": {
                    "keyword_answer": item["_keyword_answer"],
                    "reference": item["_reference"],
                    "judge_criteria": item["_judge_criteria"],
                },
                "web_search_evidence": item.get("_web_search_evidence", {}),
                "model_answer_status": item["status"],
                "llm_answer": item["llm_answer"],
            }
        )

    return textwrap.dedent(
        f"""
        You are a strict Korean RAG benchmark judge.

        Judge every item independently. The list is chunked only for transport;
        do not batch-score, do not use keyword-only matching, and do not copy a
        verdict from a neighboring row. Read each question, private judge
        reference, and llm_answer.

        Use the provided Firecrawl web_search_evidence when public facts, legal
        definitions, policy names, or dataset claims affect correctness. Prefer
        official Korean law, government, local-government, or public-data
        sources. If the evidence is sparse or the question is only verifiable
        against the private cleaned corpus reference, judge against the private
        reference and set web_check to a short note such as
        "limited to private benchmark reference". Do not invent source URLs.

        Mark "correct" only when the answer satisfies the user's intent and the
        judge criteria without contradicting the reference or public facts.
        Mark "wrong" for empty/error answers, unsupported certainty, wrong
        law/policy/dataset mapping, missing essential distinction, or factual
        conflict.

        Return exactly one top-level JSON object with this shape:
        {{"items":[{{"row_id":"...","judge_result":"correct|wrong","judge_reason":"...","web_check":"...","source_urls":["..."]}}]}}
        Do not emit markdown, duplicate JSON, or explanatory prose. For each
        row_id, include judge_result, judge_reason, web_check, and source_urls.
        judge_result must be only the literal string "correct" or "wrong";
        never put the explanation in judge_result.

        Items:
        {json.dumps(prompt_items, ensure_ascii=False, indent=2)}
        """
    ).strip()


def parse_last_message(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        return json.loads(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        decoder = json.JSONDecoder()
        parsed_values: list[Any] = []
        offset = 0
        while offset < len(candidate):
            match = re.search(r"[\[{]", candidate[offset:])
            if not match:
                break
            offset += match.start()
            try:
                value, end_offset = decoder.raw_decode(candidate[offset:])
            except json.JSONDecodeError:
                offset += 1
                continue
            parsed_values.append(value)
            offset += end_offset
        if parsed_values:
            value = parsed_values[-1]
            if isinstance(value, list):
                return {"items": value}
            return value
    raise ValueError(f"Could not parse Codex output as JSON: {text[:500]}")


def run_codex_judge(
    prompt: str,
    model: str,
    timeout_seconds: int,
    use_output_schema: bool,
    codex_search: bool,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".json") as output:
        command = [
            "codex",
            "-m",
            model,
            "-s",
            "read-only",
            "-a",
            "never",
            "exec",
            "--ephemeral",
            "--ignore-rules",
            "--output-last-message",
            output.name,
            "-",
        ]
        if codex_search:
            command.insert(1, "--search")
        if use_output_schema:
            schema_args = ["--output-schema", str(SCHEMA_PATH)]
            insert_at = command.index("--output-last-message")
            command[insert_at:insert_at] = schema_args
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            cwd=ROOT_DIR,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Codex judge failed.\n"
                f"STDOUT:\n{completed.stdout[-4000:]}\n"
                f"STDERR:\n{completed.stderr[-4000:]}"
            )
        output.flush()
        return parse_last_message(Path(output.name))


def judge_chunk_with_retry(
    chunk: list[dict[str, str]],
    model: str,
    timeout_seconds: int,
    use_output_schema: bool,
    codex_search: bool,
) -> list[dict[str, Any]]:
    row_ids = [item["row_id"] for item in chunk]
    try:
        response = run_codex_judge(
            make_prompt(chunk),
            model,
            timeout_seconds,
            use_output_schema,
            codex_search,
        )
        items = response if isinstance(response, list) else response.get("items", [])
        return normalize_and_validate_items(items, row_ids)
    except Exception as exc:
        if len(chunk) == 1:
            raise
        print(
            f"Chunk failed ({exc}); retrying {len(chunk)} rows one by one.",
            flush=True,
        )
        recovered: list[dict[str, Any]] = []
        for item in chunk:
            recovered.extend(
                judge_chunk_with_retry(
                    [item],
                    model,
                    timeout_seconds,
                    use_output_schema,
                    codex_search,
                )
            )
        return recovered


def append_checkpoint(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def normalize_and_validate_items(
    items: list[dict[str, Any]], row_ids: list[str]
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        value = dict(item)
        if "judge_result" not in value and "result" in value:
            value["judge_result"] = value["result"]
        if value.get("judge_result") not in VALID_JUDGE_RESULTS:
            raise RuntimeError(
                f"Invalid judge_result for {value.get('row_id')}: "
                f"{value.get('judge_result')!r}"
            )
        if not isinstance(value.get("judge_reason"), str):
            raise RuntimeError(f"Missing judge_reason for {value.get('row_id')}")
        if not isinstance(value.get("web_check"), str):
            value["web_check"] = ""
        if not isinstance(value.get("source_urls"), list):
            value["source_urls"] = []
        normalized.append(value)

    by_id = {item.get("row_id"): item for item in normalized}
    missing = [row_id for row_id in row_ids if row_id not in by_id]
    if missing:
        raise RuntimeError(f"Codex output missing row_ids: {missing}")
    return [by_id[row_id] for row_id in row_ids]


def write_output_csv(
    path: Path, rows: list[dict[str, str]], results: dict[str, dict[str, Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            result = results.get(row["row_id"], {})
            source_urls = result.get("source_urls", [])
            writer.writerow(
                {
                    "question_number": row["question_number"],
                    "question": row["question"],
                    "source_file": row["source_file"],
                    "model_id": row["model_id"],
                    "provider": row["provider"],
                    "actual_provider": row["actual_provider"],
                    "status": row["status"],
                    "llm_answer": row["llm_answer"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "used_tokens": row["used_tokens"],
                    "total_cost_usd": row["total_cost_usd"],
                    "latency_ms": row["latency_ms"],
                    "judge_result": result.get("judge_result", ""),
                    "judge_reason": result.get("judge_reason", ""),
                    "web_check": result.get("web_check", ""),
                    "source_urls": "; ".join(source_urls)
                    if isinstance(source_urls, list)
                    else str(source_urls),
                }
            )


def chunks(values: list[dict[str, str]], size: int):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def main() -> None:
    args = parse_args()
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be at least 1")

    questions = parse_markdown_table(args.question_set)
    rows = load_benchmark_rows(args.raw_results_dir, questions)
    if args.limit:
        rows = rows[: args.limit]

    if args.overwrite and args.checkpoint_jsonl.exists():
        args.checkpoint_jsonl.unlink()

    web_cache = ensure_web_cache(rows, args.web_cache_json, args.skip_web_search)
    for row in rows:
        row["_web_search_evidence"] = web_cache.get(row["question_number"], {})

    results = load_checkpoint(args.checkpoint_jsonl)
    pending = [row for row in rows if row["row_id"] not in results]
    print(
        f"Loaded {len(rows)} rows; {len(results)} already judged; "
        f"{len(pending)} pending.",
        flush=True,
    )

    for index, chunk in enumerate(chunks(pending, args.chunk_size), start=1):
        row_ids = [item["row_id"] for item in chunk]
        print(
            f"Judging chunk {index}: {row_ids[0]} .. {row_ids[-1]}",
            flush=True,
        )
        ordered_items = judge_chunk_with_retry(
            chunk,
            args.model,
            args.timeout_seconds,
            args.use_output_schema,
            args.codex_search,
        )
        append_checkpoint(args.checkpoint_jsonl, ordered_items)
        results.update({item["row_id"]: item for item in ordered_items})
        write_output_csv(args.output_csv, rows, results)
        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    write_output_csv(args.output_csv, rows, results)
    print(f"Wrote {args.output_csv}")


if __name__ == "__main__":
    main()
