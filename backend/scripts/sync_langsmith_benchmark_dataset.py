from __future__ import annotations

import argparse

from langsmith import Client

from langsmith_benchmark_common import (
    DEFAULT_DATASET_NAME,
    configure_env,
    parse_markdown_table,
    testcase_to_example,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update the LangSmith benchmark dataset.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_env()

    testcases = parse_markdown_table()
    if args.limit:
        testcases = testcases[: args.limit]

    examples = [testcase_to_example(args.dataset, testcase) for testcase in testcases]
    client = Client()

    try:
        dataset = client.read_dataset(dataset_name=args.dataset)
        dataset_exists = True
    except Exception:
        dataset = None
        dataset_exists = False

    print(f"dataset: {args.dataset}")
    print(f"dataset_exists: {dataset_exists}")
    print(f"examples: {len(examples)}")

    if args.dry_run:
        return

    if dataset is None:
        dataset = client.create_dataset(
            args.dataset,
            description="SKN28 RAG agent benchmark questions from rag_agent_question_test_cases.md",
            metadata={"source": "backend/tests/benchmark/data/rag_agent_question_test_cases.md"},
        )
        print(f"created_dataset_id: {dataset.id}")
    else:
        print(f"dataset_id: {dataset.id}")

    response = client.create_examples(dataset_id=dataset.id, examples=examples, max_concurrency=3)
    print(f"upsert_response: {response}")

    count = sum(1 for _ in client.list_examples(dataset_id=dataset.id, limit=10_000))
    print(f"dataset_example_count: {count}")


if __name__ == "__main__":
    main()
