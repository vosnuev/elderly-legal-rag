from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Law:
    name: str
    law_id: str
    kind: str
    ministry: str
    effective_date: str
    promulgation_no: str
    promulgation_date: str
    source_file: str

    @property
    def node_id(self) -> str:
        return f"law/{self.name}"


@dataclass(frozen=True)
class Article:
    id: str
    article: str
    title: str
    content: str
    ordinal: int
    law_name: str


@dataclass(frozen=True)
class LawDocument:
    path: Path
    law: Law
    articles: list[Article]


@dataclass(frozen=True)
class ManualRelation:
    id: str
    law_name: str
    source_article: str
    target_article: str
    source_article_id: str
    target_article_id: str
    header: str
    category: str
    relation_type: str
    summary: str
    evidence: str
    source_docx: str
    note: str

