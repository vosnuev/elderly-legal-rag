from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
TESTCASE_FILE = ROOT_DIR / "tests" / "benchmark" / "data" / "rag_agent_question_test_cases.md"
SYSTEM_PROMPT_FILE = ROOT_DIR / "src" / "prompt" / "system_prompt.j2"
DEFAULT_DATASET_NAME = "skn28-rag-agent-question-benchmark"


def configure_env() -> None:
    load_dotenv(ROOT_DIR / ".env", override=False)

    if os.environ.get("LANGSMITH_TRACING"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", os.environ["LANGSMITH_TRACING"])
    if os.environ.get("LANGSMITH_PROJECT"):
        os.environ.setdefault("LANGCHAIN_PROJECT", os.environ["LANGSMITH_PROJECT"])
    if os.environ.get("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGCHAIN_API_KEY", os.environ["LANGSMITH_API_KEY"])

    os.environ.setdefault("LANGCHAIN_CALLBACKS_BACKGROUND", "false")


def parse_markdown_table(path: Path = TESTCASE_FILE) -> list[dict[str, str]]:
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


def stable_example_id(dataset_name: str, testcase_id: str) -> uuid.UUID:
    key = f"langsmith://datasets/{dataset_name}/examples/{testcase_id}"
    return uuid.uuid5(uuid.NAMESPACE_URL, key)


def testcase_to_example(dataset_name: str, testcase: dict[str, str]) -> dict[str, Any]:
    return {
        "id": stable_example_id(dataset_name, testcase["testcase_id"]),
        "inputs": {
            "query": testcase["query"],
            "testcase_id": testcase["testcase_id"],
        },
        "outputs": {
            "expected_keywords": testcase["expected_keywords"],
            "reference": testcase["reference"],
            "judge_criteria": testcase["judge_criteria"],
        },
        "metadata": {
            "testcase_id": testcase["testcase_id"],
            "batch": testcase["batch"],
            "difficulty": testcase["difficulty"],
            "special_case": testcase["special_case"],
            "source_file": str(TESTCASE_FILE.relative_to(ROOT_DIR)),
        },
        "split": "benchmark",
    }


def required_keywords(expected_keywords: str) -> list[str]:
    prefix = "필수 키워드:"
    marker = "정답 방향:"
    if prefix not in expected_keywords:
        return []

    text = expected_keywords.split(prefix, 1)[1]
    if marker in text:
        text = text.split(marker, 1)[0]
    text = text.strip().rstrip(".")
    return [item.strip() for item in text.split(",") if item.strip()]
