from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any


JUDGE_DIR = Path(__file__).resolve().parents[1]
TEST_DATA_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[4]
RAW_CSV = (
    TEST_DATA_DIR
    / "yes-tool-benchmark"
    / "raw-results"
    / "deepseek_v4_flash_tools_yes_wrong.csv"
)
OUTPUT_DIR = JUDGE_DIR / "artifacts" / "tools-yes"
OUTPUT_CSV = OUTPUT_DIR / "llm_judge_results.csv"
SUMMARY_CSV = OUTPUT_DIR / "llm_judge_model_summary.csv"
CHECKPOINT_JSONL = OUTPUT_DIR / "llm_judge_results.checkpoint.jsonl"
SCHEMA_PATH = Path(__file__).resolve().with_name("llm_judge_output_schema.json")

VALID_JUDGE_RESULTS = {"correct", "wrong"}
NO_TOOL_TOTAL_QUESTIONS = 360
NO_TOOL_CORRECT_COUNT = 249
NO_TOOL_WRONG_COUNT = 111

OUTPUT_COLUMNS = [
    "question_number",
    "question",
    "source_file",
    "target_model_id",
    "provider",
    "status",
    "llm_answer",
    "tool_call_count",
    "tool_calls",
    "source_count",
    "sources",
    "latency_ms",
    "no_tool_model_id",
    "no_tool_provider",
    "no_tool_actual_provider",
    "no_tool_judge_result",
    "no_tool_judge_reason",
    "no_tool_total_cost_usd",
    "no_tool_latency_ms",
    "judge_result",
    "judge_reason",
    "web_check",
    "source_urls",
]

SUMMARY_COLUMNS = [
    "target_model_id",
    "provider",
    "bench_scope",
    "evaluated_wrong_questions",
    "with_tool_correct_count",
    "with_tool_wrong_count",
    "with_tool_accuracy_on_no_tool_wrongs",
    "no_tool_total_questions",
    "no_tool_correct_count",
    "no_tool_wrong_count",
    "expected_total_correct_with_tools",
    "expected_overall_accuracy_with_tools",
    "absolute_accuracy_lift",
    "avg_tool_call_count",
    "avg_source_count",
    "avg_latency_ms",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Codex LLM judge over DeepSeek V4 Flash tools-yes wrong-only CSV."
    )
    parser.add_argument("--raw-csv", type=Path, default=RAW_CSV)
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--summary-csv", type=Path, default=SUMMARY_CSV)
    parser.add_argument("--checkpoint-jsonl", type=Path, default=CHECKPOINT_JSONL)
    parser.add_argument("--chunk-size", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--model", default="gpt-5.3-codex-spark")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--use-output-schema", action="store_true")
    parser.add_argument("--codex-search", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


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


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            testcase_id = row["testcase_id"]
            query_reference = parse_query_reference(row.get("query_reference", ""))
            row_id = f"{path.name}::{testcase_id}"
            rows.append(
                {
                    "row_id": row_id,
                    "question_number": testcase_id,
                    "question": query_reference.get("query", ""),
                    "source_file": path.name,
                    "target_model_id": row.get("target_model_id", ""),
                    "provider": ",".join(
                        json.loads(row.get("expected_provider_order") or "[]")
                    ),
                    "status": row.get("status", ""),
                    "llm_answer": row.get("answer", ""),
                    "tool_call_count": row.get("tool_call_count", ""),
                    "tool_calls": row.get("tool_calls", ""),
                    "source_count": row.get("source_count", ""),
                    "sources": row.get("sources", ""),
                    "latency_ms": row.get("latency_ms", ""),
                    "no_tool_model_id": row.get("no_tool_model_id", ""),
                    "no_tool_provider": row.get("no_tool_provider", ""),
                    "no_tool_actual_provider": row.get("no_tool_actual_provider", ""),
                    "no_tool_judge_result": row.get("no_tool_judge_result", ""),
                    "no_tool_judge_reason": row.get("no_tool_judge_reason", ""),
                    "no_tool_total_cost_usd": row.get("no_tool_total_cost_usd", ""),
                    "no_tool_latency_ms": row.get("no_tool_latency_ms", ""),
                    "_keyword_answer": query_reference.get("expected_keywords", ""),
                    "_reference": query_reference.get("reference", ""),
                    "_judge_criteria": query_reference.get("judge_criteria", ""),
                    "_batch": row.get("batch", ""),
                    "_difficulty": row.get("difficulty", ""),
                    "_special_case": row.get("special_case", ""),
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
            if item.get("judge_result") in VALID_JUDGE_RESULTS:
                results[item["row_id"]] = item
    return results


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
                "with_tool_observability": {
                    "model_answer_status": item["status"],
                    "tool_call_count": item["tool_call_count"],
                    "tool_calls": item["tool_calls"],
                    "source_count": item["source_count"],
                    "sources": item["sources"],
                },
                "no_tool_baseline": {
                    "judge_result": item["no_tool_judge_result"],
                    "judge_reason": item["no_tool_judge_reason"],
                },
                "llm_answer": item["llm_answer"],
            }
        )

    return textwrap.dedent(
        f"""
        You are a pragmatic Korean RAG benchmark judge.

        Judge every item independently. These are with-tool/RAG answers for
        questions that the same target model previously answered wrong without
        tools. Do not assume improvement just because tool calls exist; score
        only the final llm_answer against the user's question and private judge
        reference.

        Mark "correct" when the answer substantially satisfies the user's intent,
        includes the essential keywords or equivalent meanings, and does not
        contradict the private reference. Do not require exact wording, a perfect
        citation format, or explicit source excerpts when the answer is otherwise
        aligned with the expected answer direction. Personal eligibility answers
        may be correct when they explain the main rule and say missing conditions
        still need confirmation.

        Mark "wrong" only for material failures: empty/error answers, clearly
        unsupported certainty, wrong law/policy/dataset mapping, missing the core
        requested concept, factual conflict with the reference, or answers that
        only ask follow-up questions without giving a usable answer.

        Use tool metadata only as supporting context. A high tool_call_count is
        not itself correctness. If the answer lacks citations but gives a useful,
        non-contradictory answer matching the expected direction, it can still be
        correct. Penalize internal fields such as row, score, query, counters, or
        invented URLs/phone numbers only when they materially harm correctness.

        Return exactly one top-level JSON object with this shape:
        {{"items":[{{"row_id":"...","judge_result":"correct|wrong","judge_reason":"...","web_check":"...","source_urls":["..."]}}]}}
        Do not emit markdown, duplicate JSON, or explanatory prose. judge_result
        must be only the literal string "correct" or "wrong".

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
            value["web_check"] = "limited to private benchmark reference"
        if not isinstance(value.get("source_urls"), list):
            value["source_urls"] = []
        normalized.append(value)

    by_id = {item.get("row_id"): item for item in normalized}
    missing = [row_id for row_id in row_ids if row_id not in by_id]
    if missing:
        raise RuntimeError(f"Codex output missing row_ids: {missing}")
    return [by_id[row_id] for row_id in row_ids]


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
                    "target_model_id": row["target_model_id"],
                    "provider": row["provider"],
                    "status": row["status"],
                    "llm_answer": row["llm_answer"],
                    "tool_call_count": row["tool_call_count"],
                    "tool_calls": row["tool_calls"],
                    "source_count": row["source_count"],
                    "sources": row["sources"],
                    "latency_ms": row["latency_ms"],
                    "no_tool_model_id": row["no_tool_model_id"],
                    "no_tool_provider": row["no_tool_provider"],
                    "no_tool_actual_provider": row["no_tool_actual_provider"],
                    "no_tool_judge_result": row["no_tool_judge_result"],
                    "no_tool_judge_reason": row["no_tool_judge_reason"],
                    "no_tool_total_cost_usd": row["no_tool_total_cost_usd"],
                    "no_tool_latency_ms": row["no_tool_latency_ms"],
                    "judge_result": result.get("judge_result", ""),
                    "judge_reason": result.get("judge_reason", ""),
                    "web_check": result.get("web_check", ""),
                    "source_urls": "; ".join(source_urls)
                    if isinstance(source_urls, list)
                    else str(source_urls),
                }
            )


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def write_summary_csv(
    path: Path, rows: list[dict[str, str]], results: dict[str, dict[str, Any]]
) -> None:
    judged_rows = [row for row in rows if row["row_id"] in results]
    correct_count = sum(
        1 for row in judged_rows if results[row["row_id"]].get("judge_result") == "correct"
    )
    wrong_count = sum(
        1 for row in judged_rows if results[row["row_id"]].get("judge_result") == "wrong"
    )
    evaluated = correct_count + wrong_count
    with_tool_accuracy = correct_count / evaluated if evaluated else 0.0
    expected_total_correct = NO_TOOL_CORRECT_COUNT + correct_count
    expected_overall_accuracy = expected_total_correct / NO_TOOL_TOTAL_QUESTIONS
    no_tool_accuracy = NO_TOOL_CORRECT_COUNT / NO_TOOL_TOTAL_QUESTIONS
    avg_tool_calls = (
        sum(to_float(row["tool_call_count"]) for row in judged_rows) / evaluated
        if evaluated
        else 0.0
    )
    avg_sources = (
        sum(to_float(row["source_count"]) for row in judged_rows) / evaluated
        if evaluated
        else 0.0
    )
    avg_latency = (
        sum(to_float(row["latency_ms"]) for row in judged_rows) / evaluated
        if evaluated
        else 0.0
    )
    first_row = rows[0] if rows else {}

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "target_model_id": first_row.get("target_model_id", ""),
                "provider": first_row.get("provider", ""),
                "bench_scope": "no-tool wrong-only",
                "evaluated_wrong_questions": str(evaluated),
                "with_tool_correct_count": str(correct_count),
                "with_tool_wrong_count": str(wrong_count),
                "with_tool_accuracy_on_no_tool_wrongs": f"{with_tool_accuracy:.6f}",
                "no_tool_total_questions": str(NO_TOOL_TOTAL_QUESTIONS),
                "no_tool_correct_count": str(NO_TOOL_CORRECT_COUNT),
                "no_tool_wrong_count": str(NO_TOOL_WRONG_COUNT),
                "expected_total_correct_with_tools": str(expected_total_correct),
                "expected_overall_accuracy_with_tools": f"{expected_overall_accuracy:.6f}",
                "absolute_accuracy_lift": f"{expected_overall_accuracy - no_tool_accuracy:.6f}",
                "avg_tool_call_count": f"{avg_tool_calls:.6f}",
                "avg_source_count": f"{avg_sources:.6f}",
                "avg_latency_ms": f"{avg_latency:.6f}",
            }
        )


def chunks(values: list[dict[str, str]], size: int):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def main() -> None:
    args = parse_args()
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be at least 1")

    rows = load_rows(args.raw_csv)
    if args.limit:
        rows = rows[: args.limit]

    if args.overwrite and args.checkpoint_jsonl.exists():
        args.checkpoint_jsonl.unlink()

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
        write_summary_csv(args.summary_csv, rows, results)
        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    write_output_csv(args.output_csv, rows, results)
    write_summary_csv(args.summary_csv, rows, results)
    print(f"Wrote {args.output_csv}")
    print(f"Wrote {args.summary_csv}")


if __name__ == "__main__":
    main()
