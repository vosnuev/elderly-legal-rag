from __future__ import annotations

import argparse
import csv
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_FILE = ROOT_DIR / "results" / "llm_validation_results.csv"
DEFAULT_OUTPUT_FILE = ROOT_DIR / "results" / "llm_validation_results_by_provider.xlsx"

INVALID_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")
NUMERIC_COLUMNS = {
    "context_length",
    "max_completion_tokens",
    "input_price_per_1m",
    "output_price_per_1m",
    "input_tokens",
    "output_tokens",
    "used_tokens",
    "input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
    "latency_ms",
    "success_count",
    "failed_count",
    "sum_input_tokens",
    "sum_output_tokens",
    "sum_used_tokens",
    "sum_total_cost_usd",
    "avg_latency_ms",
}

QUERY_COLUMNS = [
    "testcase_id",
    "query",
    "expected_keywords",
    "reference",
    "batch",
    "difficulty",
    "special_case",
]

TRANSPOSE_METRICS = [
    "status",
    "actual_provider",
    "input_tokens",
    "output_tokens",
    "used_tokens",
    "input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
    "latency_ms",
    "openrouter_generation_id",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export validation CSV to provider-grouped XLSX.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    return parser.parse_args()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("/", "_").replace("-", "_").replace(".", "_")
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def sheet_name_for(row: dict[str, str]) -> str:
    model = row.get("sheet_name") or _slug(row.get("model_id", "model"))
    provider = _slug(row.get("provider_slug") or row.get("provider_name", "provider"))
    name = f"{model}__{provider}"
    name = INVALID_SHEET_CHARS.sub("_", name)
    return name[:31]


def unique_sheet_names(names: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()

    for name in names:
        base = name[:31] or "sheet"
        candidate = base
        counter = 2
        while candidate in used:
            suffix = f"_{counter}"
            candidate = f"{base[:31 - len(suffix)]}{suffix}"
            counter += 1
        result[name] = candidate
        used.add(candidate)

    return result


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[sheet_name_for(row)].append(row)
    return dict(grouped)


def _float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key) or 0)
    except ValueError:
        return 0.0


def build_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("model_label", ""),
            row.get("model_id", ""),
            row.get("provider_name", ""),
            row.get("provider_slug", ""),
            row.get("tool_mode", ""),
        )
        grouped[key].append(row)

    summary_rows: list[dict[str, str]] = []
    for (model_label, model_id, provider_name, provider_slug, tool_mode), items in sorted(grouped.items()):
        success_items = [row for row in items if row.get("status") == "success"]
        failed_items = [row for row in items if row.get("status") != "success"]
        latencies = [_float(row, "latency_ms") for row in success_items if row.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        summary_rows.append(
            {
                "model_label": model_label,
                "model_id": model_id,
                "provider_name": provider_name,
                "provider_slug": provider_slug,
                "tool_mode": tool_mode,
                "success_count": str(len(success_items)),
                "failed_count": str(len(failed_items)),
                "sum_input_tokens": str(int(sum(_float(row, "input_tokens") for row in success_items))),
                "sum_output_tokens": str(int(sum(_float(row, "output_tokens") for row in success_items))),
                "sum_used_tokens": str(int(sum(_float(row, "used_tokens") for row in success_items))),
                "sum_total_cost_usd": f"{sum(_float(row, 'total_cost_usd') for row in success_items):.10f}".rstrip("0").rstrip("."),
                "avg_latency_ms": f"{avg_latency:.2f}".rstrip("0").rstrip("."),
            }
        )

    return summary_rows


def build_queries(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_testcase: dict[str, dict[str, str]] = {}
    for row in rows:
        testcase_id = row.get("testcase_id", "")
        if testcase_id and testcase_id not in by_testcase:
            by_testcase[testcase_id] = {column: row.get(column, "") for column in QUERY_COLUMNS}

    return [by_testcase[testcase_id] for testcase_id in sorted(by_testcase)]


def build_transposed_provider_rows(rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    testcase_ids = sorted({row.get("testcase_id", "") for row in rows if row.get("testcase_id")})
    by_mode_and_testcase: dict[tuple[str, str], dict[str, str]] = {}
    tool_modes = sorted({row.get("tool_mode", "unknown") or "unknown" for row in rows})

    for row in rows:
        tool_mode = row.get("tool_mode", "unknown") or "unknown"
        testcase_id = row.get("testcase_id", "")
        if testcase_id:
            by_mode_and_testcase[(tool_mode, testcase_id)] = row

    transposed_rows: list[dict[str, str]] = []
    for tool_mode in tool_modes:
        for metric in TRANSPOSE_METRICS:
            metric_row = {"metric": f"{tool_mode}.{metric}"}
            for testcase_id in testcase_ids:
                source = by_mode_and_testcase.get((tool_mode, testcase_id), {})
                metric_row[testcase_id] = source.get(metric, "")
            transposed_rows.append(metric_row)

    return ["metric", *testcase_ids], transposed_rows


def column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def is_number(value: str) -> bool:
    if value == "":
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False


def cell_xml(row_index: int, column_index: int, header: str, value: str) -> str:
    ref = f"{column_name(column_index)}{row_index}"
    if (header in NUMERIC_COLUMNS or header.startswith("RAG-Q-")) and is_number(value):
        return f'<c r="{ref}" t="n"><v>{escape(value)}</v></c>'

    return (
        f'<c r="{ref}" t="inlineStr">'
        f"<is><t>{escape(value)}</t></is>"
        f"</c>"
    )


def worksheet_xml(headers: list[str], rows: list[dict[str, str]]) -> str:
    xml_rows = []
    header_cells = [
        cell_xml(1, index, header, header)
        for index, header in enumerate(headers, start=1)
    ]
    xml_rows.append(f'<row r="1">{"".join(header_cells)}</row>')

    for row_number, row in enumerate(rows, start=2):
        cells = [
            cell_xml(row_number, index, header, str(row.get(header, "")))
            for index, header in enumerate(headers, start=1)
        ]
        xml_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(xml_rows)}</sheetData>"
        "</worksheet>"
    )


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = []
    for index, sheet_name in enumerate(sheet_names, start=1):
        sheets.append(
            f'<sheet name="{escape(sheet_name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{''.join(sheets)}</sheets>"
        "</workbook>"
    )


def workbook_rels_xml(sheet_count: int) -> str:
    rels = []
    for index in range(1, sheet_count + 1):
        rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    style_id = sheet_count + 1
    rels.append(
        f'<Relationship Id="rId{style_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{''.join(rels)}"
        "</Relationships>"
    )


def content_types_xml(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f"{''.join(overrides)}"
        "</Types>"
    )


def root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        "</styleSheet>"
    )


def core_xml() -> str:
    now = datetime.now(timezone.utc).isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>LLM Validation Results</dc:title>"
        "<dc:creator>backend validation script</dc:creator>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def app_xml(sheet_count: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>backend validation script</Application>"
        f"<TitlesOfParts><vt:vector size=\"{sheet_count}\" baseType=\"lpstr\"></vt:vector></TitlesOfParts>"
        "</Properties>"
    )


def write_xlsx(
    output: Path,
    csv_headers: list[str],
    rows: list[dict[str, str]],
) -> None:
    grouped = group_rows(rows)
    unique_names = unique_sheet_names(["summary", "queries", *grouped.keys()])

    summary_headers = [
        "model_label",
        "model_id",
        "provider_name",
        "provider_slug",
        "tool_mode",
        "success_count",
        "failed_count",
        "sum_input_tokens",
        "sum_output_tokens",
        "sum_used_tokens",
        "sum_total_cost_usd",
        "avg_latency_ms",
    ]
    sheets: list[tuple[str, list[str], list[dict[str, str]]]] = [
        (unique_names["summary"], summary_headers, build_summary(rows)),
        (unique_names["queries"], QUERY_COLUMNS, build_queries(rows)),
    ]

    for raw_name, sheet_rows in sorted(grouped.items()):
        transposed_headers, transposed_rows = build_transposed_provider_rows(sheet_rows)
        sheets.append((unique_names[raw_name], transposed_headers, transposed_rows))

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", root_rels_xml())
        archive.writestr("docProps/core.xml", core_xml())
        archive.writestr("docProps/app.xml", app_xml(len(sheets)))
        archive.writestr("xl/workbook.xml", workbook_xml([sheet[0] for sheet in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(len(sheets)))
        archive.writestr("xl/styles.xml", styles_xml())

        for index, (_, headers, sheet_rows) in enumerate(sheets, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                worksheet_xml(headers, sheet_rows),
            )


def main() -> None:
    args = parse_args()
    headers, rows = read_rows(args.input)
    write_xlsx(args.output, headers, rows)
    print(f"wrote XLSX: {args.output}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
