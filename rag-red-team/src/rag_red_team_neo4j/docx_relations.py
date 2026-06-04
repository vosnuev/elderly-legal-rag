from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph

from .models import ManualRelation


RELATION_RE = re.compile(
    r"^(?P<src_index>\d{3})_(?P<src_article>제\d+조(?:의\d+)?)"
    r"(?:_(?P<src_title>.*?))?\s*→\s*"
    r"(?P<target_index>\d{3})_(?P<target_article>제\d+조(?:의\d+)?)"
    r"(?:_(?P<target_title>.*?))?"
    r"(?:\s*\((?P<note>.*?)\))?$"
)


@dataclass(frozen=True)
class ParagraphInfo:
    text: str
    all_bold: bool


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def _is_all_bold(paragraph: Paragraph) -> bool:
    runs = [run for run in paragraph.runs if run.text.strip()]
    return bool(runs) and all(run.bold is True for run in runs)


def _paragraph_infos(path: Path) -> list[ParagraphInfo]:
    document = Document(path)
    infos: list[ParagraphInfo] = []
    for paragraph in document.paragraphs:
        text = _normalize_text(paragraph.text)
        if text:
            infos.append(ParagraphInfo(text=text, all_bold=_is_all_bold(paragraph)))
    return infos


def _is_relation_header(text: str) -> bool:
    return RELATION_RE.match(text) is not None


def _is_category(infos: list[ParagraphInfo], index: int) -> bool:
    if index + 1 >= len(infos):
        return False
    current = infos[index]
    next_text = infos[index + 1].text
    return (
        current.all_bold
        and not _is_relation_header(current.text)
        and _is_relation_header(next_text)
        and len(current.text) <= 50
    )


def _normalize_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", name)


def infer_law_name(docx_path: Path, known_law_names: list[str]) -> str:
    stem = docx_path.stem
    normalized_stem = _normalize_name(stem)
    scored = [
        (
            SequenceMatcher(None, normalized_stem, _normalize_name(law_name)).ratio(),
            law_name,
        )
        for law_name in known_law_names
    ]
    score, law_name = max(scored, key=lambda item: item[0])
    if score < 0.45:
        raise ValueError(f"Could not infer law name for {docx_path.name}")
    return law_name


def _article_id(law_name: str, article: str) -> str:
    return f"law/{law_name}/{article}"


def _relation_id(law_name: str, header: str, source: str, target: str) -> str:
    digest = hashlib.sha1(
        f"{law_name}|{header}|{source}|{target}".encode("utf-8")
    ).hexdigest()[:16]
    return f"manual-relation/{digest}"


def _extract_summary(block_lines: list[str]) -> str:
    for index, line in enumerate(block_lines[:-1]):
        if "한 줄 요약" in line:
            return block_lines[index + 1]
    for line in block_lines:
        if not line.endswith(":") and not line.startswith(("①", "②", "③", "④", "⑤")):
            return line
    return ""


def _extract_relation_type(block_lines: list[str], note: str, category: str) -> str:
    for index, line in enumerate(block_lines[:-1]):
        if "관계 유형" in line:
            return block_lines[index + 1]
    if note:
        return note
    return category


def parse_manual_relations(docx_dir: Path, known_law_names: list[str]) -> list[ManualRelation]:
    paths = sorted(docx_dir.glob("*.docx"))
    if not paths:
        raise FileNotFoundError(f"No .docx files found under {docx_dir}")

    relations: list[ManualRelation] = []
    for path in paths:
        law_name = infer_law_name(path, known_law_names)
        infos = _paragraph_infos(path)
        category = ""
        index = 0
        while index < len(infos):
            if _is_category(infos, index):
                category = infos[index].text
                index += 1
                continue

            header = infos[index].text
            match = RELATION_RE.match(header)
            if not match:
                index += 1
                continue

            block_lines: list[str] = []
            cursor = index + 1
            while cursor < len(infos):
                if _is_relation_header(infos[cursor].text) or _is_category(infos, cursor):
                    break
                block_lines.append(infos[cursor].text)
                cursor += 1

            source_article = match.group("src_article")
            target_article = match.group("target_article")
            note = _normalize_text(match.group("note") or "")
            relations.append(
                ManualRelation(
                    id=_relation_id(law_name, header, source_article, target_article),
                    law_name=law_name,
                    source_article=source_article,
                    target_article=target_article,
                    source_article_id=_article_id(law_name, source_article),
                    target_article_id=_article_id(law_name, target_article),
                    header=header,
                    category=category,
                    relation_type=_extract_relation_type(block_lines, note, category),
                    summary=_extract_summary(block_lines),
                    evidence="\n".join(block_lines).strip(),
                    source_docx=path.name,
                    note=note,
                )
            )
            index = cursor

    return relations

