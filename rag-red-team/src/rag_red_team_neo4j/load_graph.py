from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from neo4j.exceptions import ServiceUnavailable

from .config import MARKDOWN_DIR, TOON_DIR, load_config
from .graph_builder import populate_graph


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate the RAG red-team Neo4j graph from TOON and Markdown design data."
    )
    parser.add_argument("--toon-dir", type=Path, default=TOON_DIR)
    parser.add_argument("--md-dir", type=Path, default=MARKDOWN_DIR)
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument("--retries", type=int, default=20)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = load_config()
    last_error: Exception | None = None

    for _ in range(args.retries):
        try:
            counts = populate_graph(
                config=config,
                toon_dir=args.toon_dir,
                md_dir=args.md_dir,
                reset=not args.no_reset,
            )
            print(json.dumps(counts, ensure_ascii=False, indent=2))
            return
        except ServiceUnavailable as exc:
            last_error = exc
            time.sleep(args.retry_delay)

    if last_error is not None:
        raise last_error


if __name__ == "__main__":
    main()
