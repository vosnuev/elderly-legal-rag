from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from .models import Article, LawDocument, ManualRelation


BOLD_LINE_RE = re.compile(r"^\*\*(?P<body>.+?)\*\*$")
ARTICLE_REF_RE = re.compile(r"(?P<index>\d{3})(?:\s*_\s*(?P<article>제\d+조(?:의\d+)?))?")
TRAILING_NOTE_RE = re.compile(r"\((?P<note>[^()]*)\)\s*$")


@dataclass(frozen=True)
class ArticleRef:
    ordinal: int
    article: str


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def _normalize_header(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\\_", "_")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_bold(line: str) -> str | None:
    match = BOLD_LINE_RE.match(line.strip())
    if not match:
        return None
    return _normalize_header(match.group("body"))


def _normalize_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", name)


def _infer_law_name(path: Path, law_names: list[str]) -> str:
    normalized_stem = _normalize_name(path.stem)
    scored = [
        (
            SequenceMatcher(None, normalized_stem, _normalize_name(law_name)).ratio(),
            law_name,
        )
        for law_name in law_names
    ]
    score, law_name = max(scored, key=lambda item: item[0])
    if score < 0.45:
        raise ValueError(f"Could not infer law name for {path.name}")
    return law_name


def _extract_refs(side: str) -> list[ArticleRef]:
    refs: list[ArticleRef] = []
    for match in ARTICLE_REF_RE.finditer(side):
        refs.append(
            ArticleRef(
                ordinal=int(match.group("index")),
                article=match.group("article") or "",
            )
        )
    return refs


def _is_edge_header(body: str) -> bool:
    if "→" not in body:
        return False
    source_side, target_side = body.split("→", 1)
    return bool(_extract_refs(source_side) and _extract_refs(target_side))


def _relation_id(path: Path, header: str, source_id: str, target_id: str) -> str:
    digest = hashlib.sha1(
        f"{path.name}|{header}|{source_id}|{target_id}".encode("utf-8")
    ).hexdigest()[:16]
    return f"markdown-relation/{digest}"


def _clean_line(line: str) -> str:
    line = line.strip()
    bold = _strip_bold(line)
    if bold is not None:
        line = bold
    line = line.strip("`")
    return _normalize_text(line)


def _extract_summary(block_lines: list[str]) -> str:
    cleaned = [_clean_line(line) for line in block_lines]
    for index, line in enumerate(cleaned[:-1]):
        if "한 줄 요약" in line:
            for candidate in cleaned[index + 1 :]:
                if candidate and "한 줄 요약" not in candidate:
                    return candidate
    for line in cleaned:
        if line and not line.endswith(":") and "관계 유형" not in line:
            return line
    return ""


def _extract_relation_type(block_lines: list[str], note: str, category: str) -> str:
    if "연관없음" in note:
        return "not_related"
    if "약" in note and "연관" in note:
        return "weak_relation"

    cleaned = [_clean_line(line) for line in block_lines]
    for index, line in enumerate(cleaned[:-1]):
        if "관계 유형" in line:
            for candidate in cleaned[index + 1 :]:
                if candidate and "관계 유형" not in candidate:
                    return candidate
    return note or category


def _resolve_article(
    ref: ArticleRef,
    articles_by_article: dict[str, Article],
    articles_by_ordinal: dict[int, Article],
    header: str,
    path: Path,
) -> Article:
    if ref.article and ref.article in articles_by_article:
        return articles_by_article[ref.article]
    if ref.ordinal in articles_by_ordinal:
        return articles_by_ordinal[ref.ordinal]
    raise ValueError(f"Could not resolve {ref!r} from {path.name}: {header}")


def _build_relations_from_block(
    path: Path,
    law_name: str,
    header: str,
    category: str,
    block_lines: list[str],
    articles_by_article: dict[str, Article],
    articles_by_ordinal: dict[int, Article],
) -> list[ManualRelation]:
    source_side, target_side = header.split("→", 1)
    source_refs = _extract_refs(source_side)
    target_refs = _extract_refs(target_side)
    note_match = TRAILING_NOTE_RE.search(header)
    note = _normalize_text(note_match.group("note") if note_match else "")
    summary = _extract_summary(block_lines)
    relation_type = _extract_relation_type(block_lines, note, category)
    evidence = "\n".join(line.rstrip() for line in block_lines).strip()

    relations: list[ManualRelation] = []
    for source_ref in source_refs:
        for target_ref in target_refs:
            source = _resolve_article(
                source_ref,
                articles_by_article,
                articles_by_ordinal,
                header,
                path,
            )
            target = _resolve_article(
                target_ref,
                articles_by_article,
                articles_by_ordinal,
                header,
                path,
            )
            relations.append(
                ManualRelation(
                    id=_relation_id(path, header, source.id, target.id),
                    law_name=law_name,
                    source_article=source.article,
                    target_article=target.article,
                    source_article_id=source.id,
                    target_article_id=target.id,
                    header=header,
                    category=category,
                    relation_type=relation_type,
                    summary=summary,
                    evidence=evidence,
                    source_docx=path.name,
                    note=note,
                )
            )
    return relations


def parse_markdown_relations(md_dir: Path, documents: list[LawDocument]) -> list[ManualRelation]:
    paths = sorted(path for path in md_dir.glob("*.md") if path.name != "README.md")
    if not paths:
        raise FileNotFoundError(f"No .md files found under {md_dir}")

    documents_by_law = {document.law.name: document for document in documents}
    law_names = list(documents_by_law)
    relations: list[ManualRelation] = []

    for path in paths:
        law_name = _infer_law_name(path, law_names)
        document = documents_by_law[law_name]
        articles_by_article = {article.article: article for article in document.articles}
        articles_by_ordinal = {article.ordinal: article for article in document.articles}

        category = ""
        current_header: str | None = None
        current_block: list[str] = []

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.rstrip()
            bold_body = _strip_bold(line)
            if bold_body is not None and _is_edge_header(bold_body):
                if current_header is not None:
                    relations.extend(
                        _build_relations_from_block(
                            path,
                            law_name,
                            current_header,
                            category,
                            current_block,
                            articles_by_article,
                            articles_by_ordinal,
                        )
                    )
                current_header = bold_body
                current_block = []
                continue

            if current_header is None:
                if bold_body is not None:
                    category = bold_body
                continue

            current_block.append(line)

        if current_header is not None:
            relations.extend(
                _build_relations_from_block(
                    path,
                    law_name,
                    current_header,
                    category,
                    current_block,
                    articles_by_article,
                    articles_by_ordinal,
                )
            )

    return relations
