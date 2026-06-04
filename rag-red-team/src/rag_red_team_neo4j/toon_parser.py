from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Article, Law, LawDocument


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _documents_key(data: dict[str, Any]) -> str:
    for key in data:
        if key.startswith("documents["):
            return key
    raise ValueError("TOON file does not contain a documents[...] section")


def parse_toon_file(path: Path) -> LawDocument:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    law_data = data["law"]
    law = Law(
        name=_string(law_data.get("name")),
        law_id=_string(law_data.get("law_id")),
        kind=_string(law_data.get("kind")),
        ministry=_string(law_data.get("ministry")),
        effective_date=_string(law_data.get("effective_date")),
        promulgation_no=_string(law_data.get("promulgation_no")),
        promulgation_date=_string(law_data.get("promulgation_date")),
        source_file=_string(data.get("source_file")),
    )

    raw_articles = data[_documents_key(data)] or []
    articles = [
        Article(
            id=_string(item.get("id")),
            article=_string(item.get("article")),
            title=_string(item.get("title")),
            content=_string(item.get("content")).strip(),
            ordinal=index,
            law_name=law.name,
        )
        for index, item in enumerate(raw_articles, start=1)
    ]

    return LawDocument(path=path, law=law, articles=articles)


def load_toon_documents(toon_dir: Path) -> list[LawDocument]:
    paths = sorted(toon_dir.glob("*.toon"))
    if not paths:
        raise FileNotFoundError(f"No .toon files found under {toon_dir}")
    return [parse_toon_file(path) for path in paths]

