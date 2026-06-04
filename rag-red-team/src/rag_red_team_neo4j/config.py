from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOON_DIR = PROJECT_ROOT / "original-data-toon"
DOCX_DIR = PROJECT_ROOT / "original-data-with-chunk-and-edge"
MARKDOWN_DIR = PROJECT_ROOT / "original-data-with-chunk-and-edge-md"


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str


def load_config() -> Neo4jConfig:
    load_dotenv(PROJECT_ROOT / ".env")

    return Neo4jConfig(
        uri=os.getenv("NEO4J_URI", "bolt://127.0.0.1:7688"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "1234"),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
