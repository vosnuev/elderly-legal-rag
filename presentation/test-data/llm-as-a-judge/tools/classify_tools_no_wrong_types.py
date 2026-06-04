from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TOOLS_NO_DIR = (
    REPO_ROOT
    / "presentation"
    / "test-data"
    / "llm-as-a-judge"
    / "artifacts"
    / "tools-no"
)
DEFAULT_RESULTS = TOOLS_NO_DIR / "llm_judge_results.csv"
DEFAULT_SUMMARY = TOOLS_NO_DIR / "llm_judge_model_summary.csv"
DEFAULT_ENUM = TOOLS_NO_DIR / "wrong_type_enum.csv"
DEFAULT_TYPE_SUMMARY = TOOLS_NO_DIR / "wrong_type_summary.csv"
DEFAULT_BY_MODEL_DIR = TOOLS_NO_DIR / "by-model"

WRONG_TYPES = [
    (
        "OUTPUT_FAILURE",
        "실제 답변 대신 오류/검색 호출/빈 응답 등 출력 형식 자체가 실패한 경우",
    ),
    (
        "UNSUPPORTED_HALLUCINATION",
        "근거 없는 수치, 시설명, 정책명, 요건을 임의로 단정하거나 사실과 충돌한 경우",
    ),
    (
        "MISSING_ACTUAL_DATA",
        "질문이 요구한 시설명, 주소, 급여, 회사명, 목록, 현황, 수치 등 구체 데이터를 제시하지 못한 경우",
    ),
    (
        "SOURCE_MAPPING_ERROR",
        "법령, 조례, 정책, 문서, 데이터셋을 잘못 매핑하거나 핵심 근거 문서를 빠뜨린 경우",
    ),
    (
        "SCOPE_FILTER_ERROR",
        "지역, 연도, 시점, 대상, 필터 조건을 잘못 적용하거나 범위를 흐린 경우",
    ),
    (
        "MISSING_CONDITIONAL_LIMITATION",
        "개인별 확정 가능성, 수급/신청/위반 여부의 조건부 판단과 추가 확인 필요성을 누락한 경우",
    ),
    (
        "OVERGENERALIZED_UNGROUNDED",
        "자료 기반 답변 대신 일반론, 전국 공통 설명, 추정적 종합으로 답한 경우",
    ),
    (
        "INCOMPLETE_CRITERIA",
        "필수 키워드, 핵심 항목, 조문/기준, 사용자 요구의 일부가 빠져 판정 기준을 충족하지 못한 경우",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify tools-no LLM judge wrong rows into primary error enums."
    )
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--enum-output", type=Path, default=DEFAULT_ENUM)
    parser.add_argument("--type-summary", type=Path, default=DEFAULT_TYPE_SUMMARY)
    parser.add_argument("--by-model-dir", type=Path, default=DEFAULT_BY_MODEL_DIR)
    return parser.parse_args()


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def classify_wrong_type(row: dict[str, str]) -> str:
    text = row.get("judge_reason", "")

    if has_any(
        text,
        [
            r"웹 검색 호출 문자열",
            r"실제 답변이 아닌",
            r"빈\s*응답",
            r"오류\s*답변",
            r"empty|error",
        ],
    ):
        return "OUTPUT_FAILURE"

    if has_any(
        text,
        [
            r"법령|조례|조문|문서|자료명|데이터셋|근거 문서|제도명|정책명",
            r"매핑|혼용|핵심 문서|근거 법령|법적 근거",
            r"근로자퇴직급여|고용보험법|기초연금법|노인복지법|최저임금법",
        ],
    ) and has_any(
        text,
        [
            r"부정확|불명확|누락|빠졌|부족|잘못|혼동|벗어|충족하지",
        ],
    ):
        return "SOURCE_MAPPING_ERROR"

    if has_any(
        text,
        [
            r"지역|해운대구|강남구|광산구|달서구|고령군|세종|서울|부산|경북|경기|울산|인천|대전|제주|충남|충북|광주",
            r"연도|2025|2026|2027|최신|시점",
            r"필터|조건에 맞는|마감일|상시채용|범위|구분",
        ],
    ) and has_any(
        text,
        [
            r"반영하지|적용하지|흐려|범위가|불일치|혼재|구분하지|정합성이 낮|충족하지|오류",
        ],
    ):
        return "SCOPE_FILTER_ERROR"

    if has_any(
        text,
        [
            r"개인별|개별|확정 가능|확정 여부|추가 확인|확인 필요",
            r"조건부|수급|신청 가능|자동|무조건|위반|소득인정액|감액|종결|중단|자격 판정",
        ],
    ) and has_any(
        text,
        [
            r"누락|부족|빠졌|단정|명확히 하지|분리하지|충족하지",
        ],
    ):
        return "MISSING_CONDITIONAL_LIMITATION"

    if has_any(
        text,
        [
            r"근거 없이",
            r"공개 근거 없이",
            r"근거가 불명",
            r"근거 미제시",
            r"근거 미확인",
            r"임의",
            r"추정",
            r"창작",
            r"단정",
            r"확정형",
            r"사실과 충돌",
            r"상충",
            r"불일치",
            r"모순",
            r"잘못",
            r"틀렸",
            r"사실성에 문제",
            r"사실 신뢰성",
            r"사실 확인 없이",
            r"정확하지",
            r"오도",
            r"확인되지",
            r"존재 여부가 불명확",
        ],
    ):
        return "UNSUPPORTED_HALLUCINATION"

    if has_any(
        text,
        [
            r"시설명|주소|급여|근무지역|회사명|제목|문의처|정원|현원|시설 수|수량",
            r"목록|명단|공고 목록|현황 정보|결과값",
            r"제시하지|제공하지|추출해 제시하지|반환하지",
            r"조회 방법|확인 방법|검색 방법|조회 절차|조회 기관",
            r"자료 없음|확인 불가|제공 불가",
        ],
    ):
        return "MISSING_ACTUAL_DATA"

    if has_any(
        text,
        [
            r"일반화|일반론|전국 공통|일반적|추정적 종합|자료 기준.*불충분",
            r"private.*기준|문서를 직접 인용하지|자료 기반.*부족|직접 대응이 불분명",
        ],
    ):
        return "OVERGENERALIZED_UNGROUNDED"

    return "INCOMPLETE_CRITERIA"


def numeric(value: str) -> float | None:
    try:
        if value == "":
            return None
        return float(value)
    except ValueError:
        return None


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def slug(value: str) -> str:
    text = value.strip().lower().replace("/", "_")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def main() -> None:
    args = parse_args()

    with args.results.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        result_fields = list(reader.fieldnames or [])

    if "wrong_type" not in result_fields:
        result_fields.append("wrong_type")

    for row in rows:
        row["wrong_type"] = (
            classify_wrong_type(row) if row.get("judge_result") == "wrong" else ""
        )

    write_csv(args.results, rows, result_fields)

    enum_counts = Counter(row["wrong_type"] for row in rows if row.get("wrong_type"))
    enum_rows = [
        {
            "wrong_type": wrong_type,
            "description": description,
            "total_count": enum_counts.get(wrong_type, 0),
            "total_ratio_of_wrong": (
                f"{enum_counts.get(wrong_type, 0) / sum(enum_counts.values()):.6f}"
                if sum(enum_counts.values())
                else ""
            ),
        }
        for wrong_type, description in WRONG_TYPES
    ]
    write_csv(
        args.enum_output,
        enum_rows,
        ["wrong_type", "description", "total_count", "total_ratio_of_wrong"],
    )

    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["source_file"], row["model_id"], row["provider"])].append(row)

    summary_base_fields = [
        "source_file",
        "model_id",
        "provider",
        "total_questions",
        "correct_count",
        "wrong_count",
        "accuracy",
        "avg_used_tokens",
        "avg_total_cost_usd",
        "avg_latency_ms",
    ]
    type_fields: list[str] = []
    for wrong_type, _description in WRONG_TYPES:
        type_fields.extend(
            [
                f"{wrong_type.lower()}_count",
                f"{wrong_type.lower()}_ratio",
            ]
        )
    summary_fields = summary_base_fields + type_fields

    summary_rows: list[dict[str, str]] = []
    type_summary_rows: list[dict[str, str]] = []
    for (source_file, model_id, provider), group_rows in sorted(groups.items()):
        total = len(group_rows)
        correct = sum(1 for row in group_rows if row.get("judge_result") == "correct")
        wrong = sum(1 for row in group_rows if row.get("judge_result") == "wrong")
        used_values = [
            value
            for row in group_rows
            if (value := numeric(row.get("used_tokens", ""))) is not None
        ]
        cost_values = [
            value
            for row in group_rows
            if (value := numeric(row.get("total_cost_usd", ""))) is not None
        ]
        latency_values = [
            value
            for row in group_rows
            if (value := numeric(row.get("latency_ms", ""))) is not None
        ]
        type_counts = Counter(
            row["wrong_type"] for row in group_rows if row.get("wrong_type")
        )
        summary_row = {
            "source_file": source_file,
            "model_id": model_id,
            "provider": provider,
            "total_questions": str(total),
            "correct_count": str(correct),
            "wrong_count": str(wrong),
            "accuracy": f"{correct / total:.6f}" if total else "",
            "avg_used_tokens": (
                f"{sum(used_values) / len(used_values):.2f}" if used_values else ""
            ),
            "avg_total_cost_usd": (
                f"{sum(cost_values) / len(cost_values):.8f}" if cost_values else ""
            ),
            "avg_latency_ms": (
                f"{sum(latency_values) / len(latency_values):.2f}"
                if latency_values
                else ""
            ),
        }
        for wrong_type, _description in WRONG_TYPES:
            count = type_counts.get(wrong_type, 0)
            summary_row[f"{wrong_type.lower()}_count"] = str(count)
            summary_row[f"{wrong_type.lower()}_ratio"] = (
                f"{count / wrong:.6f}" if wrong else "0.000000"
            )
            type_summary_rows.append(
                {
                    "source_file": source_file,
                    "model_id": model_id,
                    "provider": provider,
                    "wrong_type": wrong_type,
                    "wrong_type_count": str(count),
                    "wrong_type_ratio_of_wrong": (
                        f"{count / wrong:.6f}" if wrong else "0.000000"
                    ),
                    "wrong_count": str(wrong),
                }
            )
        summary_rows.append(summary_row)

    write_csv(args.summary, summary_rows, summary_fields)
    write_csv(
        args.type_summary,
        type_summary_rows,
        [
            "source_file",
            "model_id",
            "provider",
            "wrong_type",
            "wrong_type_count",
            "wrong_type_ratio_of_wrong",
            "wrong_count",
        ],
    )

    args.by_model_dir.mkdir(parents=True, exist_ok=True)
    for stale in args.by_model_dir.glob("llm_judge_results*.csv"):
        stale.unlink()
    by_model: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_model[row["model_id"]].append(row)

    no_answer_fields = [field for field in result_fields if field != "llm_answer"]
    for model_id, model_rows in sorted(by_model.items()):
        write_csv(
            args.by_model_dir / f"llm_judge_results__{slug(model_id)}.csv",
            model_rows,
            result_fields,
        )
        write_csv(
            args.by_model_dir
            / f"llm_judge_results_no_llm_answer__{slug(model_id)}.csv",
            [
                {field: row.get(field, "") for field in no_answer_fields}
                for row in model_rows
            ],
            no_answer_fields,
        )

    print(f"classified wrong rows: {sum(enum_counts.values())}")
    print(f"wrote {args.results}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.enum_output}")
    print(f"wrote {args.type_summary}")


if __name__ == "__main__":
    main()
