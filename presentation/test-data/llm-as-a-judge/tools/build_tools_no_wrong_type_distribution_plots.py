from __future__ import annotations

import argparse
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
DEFAULT_WRONG_TYPE_SUMMARY = TOOLS_NO_DIR / "wrong_type_summary.csv"
DEFAULT_CHARTS_DIR = TOOLS_NO_DIR / "charts"

MODEL_ORDER = {
    "deepseek_v4_flash_deepseek.csv": 1,
    "deepseek_v4_pro_deepseek.csv": 2,
    "openai_gpt_oss_120b_cerebras_fp16.csv": 3,
    "qwen_qwen3_7_plus_alibaba.csv": 4,
}

MODEL_LABELS = {
    "deepseek/deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro",
    "openai/gpt-oss-120b": "GPT-OSS 120B",
    "qwen/qwen3.7-plus": "Qwen3.7 Plus",
}

TYPE_ORDER = [
    "SOURCE_MAPPING_ERROR",
    "MISSING_ACTUAL_DATA",
    "UNSUPPORTED_HALLUCINATION",
    "SCOPE_FILTER_ERROR",
    "MISSING_CONDITIONAL_LIMITATION",
    "INCOMPLETE_CRITERIA",
    "OVERGENERALIZED_UNGROUNDED",
    "OUTPUT_FAILURE",
]

TYPE_LABELS = {
    "SOURCE_MAPPING_ERROR": "자료/법령 매핑 오류",
    "MISSING_ACTUAL_DATA": "구체 데이터 미제시",
    "UNSUPPORTED_HALLUCINATION": "근거 없는 단정/환각",
    "SCOPE_FILTER_ERROR": "범위/필터 오류",
    "MISSING_CONDITIONAL_LIMITATION": "조건부 판단 누락",
    "INCOMPLETE_CRITERIA": "기준 일부 누락",
    "OVERGENERALIZED_UNGROUNDED": "일반론/근거 부족",
    "OUTPUT_FAILURE": "출력 실패",
}

TYPE_COLORS = {
    "SOURCE_MAPPING_ERROR": "#2563EB",
    "MISSING_ACTUAL_DATA": "#16A34A",
    "UNSUPPORTED_HALLUCINATION": "#EF4444",
    "SCOPE_FILTER_ERROR": "#F97316",
    "MISSING_CONDITIONAL_LIMITATION": "#7C3AED",
    "INCOMPLETE_CRITERIA": "#64748B",
    "OVERGENERALIZED_UNGROUNDED": "#14B8A6",
    "OUTPUT_FAILURE": "#111827",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build no-tool wrong type distribution plots by model."
    )
    parser.add_argument(
        "--wrong-type-summary", type=Path, default=DEFAULT_WRONG_TYPE_SUMMARY
    )
    parser.add_argument("--charts-dir", type=Path, default=DEFAULT_CHARTS_DIR)
    return parser.parse_args()


def import_libs():
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "pandas/matplotlib are required. Example:\n"
            "cd backend && uv run --with pandas --with matplotlib "
            "python ../presentation/test-data/llm-as-a-judge/tools/"
            "build_tools_no_wrong_type_distribution_plots.py"
        ) from exc

    return pd, plt


def display_model(model_id: str, provider: str) -> str:
    label = MODEL_LABELS.get(model_id, model_id.split("/", 1)[-1])
    return f"{label}\n{provider}"


def set_plot_style(plt) -> None:
    try:
        from matplotlib import font_manager
    except ImportError:
        font_manager = None

    if font_manager is not None:
        available_fonts = {font.name for font in font_manager.fontManager.ttflist}
        for font_name in ("AppleGothic", "NanumGothic", "Malgun Gothic"):
            if font_name in available_fonts:
                plt.rcParams["font.family"] = font_name
                break

    plt.rcParams.update(
        {
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "axes.edgecolor": "#D1D5DB",
            "axes.labelcolor": "#111827",
            "axes.titleweight": "bold",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "xtick.labelsize": 10,
            "ytick.labelsize": 11,
            "legend.fontsize": 10,
            "font.size": 12,
            "axes.unicode_minus": False,
        }
    )


def load_summary(pd, path: Path):
    if not path.exists():
        raise SystemExit(f"Missing wrong type summary: {path}")
    data = pd.read_csv(path)
    for column in ["wrong_type_count", "wrong_type_ratio_of_wrong", "wrong_count"]:
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0)
    data["sort_order"] = data["source_file"].map(lambda value: MODEL_ORDER.get(value, 999))
    data["model_label"] = [
        display_model(model_id, provider)
        for model_id, provider in zip(data["model_id"], data["provider"], strict=False)
    ]
    data["wrong_type"] = pd.Categorical(data["wrong_type"], TYPE_ORDER, ordered=True)
    return data.sort_values(["sort_order", "wrong_type"])


def pivot_for(data, value_column: str):
    pivot = data.pivot_table(
        index=["sort_order", "model_label", "wrong_count"],
        columns="wrong_type",
        values=value_column,
        aggfunc="sum",
        fill_value=0,
        observed=False,
    ).reset_index()
    return pivot.sort_values("sort_order")


def draw_stacked_bar(
    plt,
    pivot,
    value_columns: list[str],
    *,
    title: str,
    ylabel: str,
    filename: Path,
    percentage: bool,
) -> None:
    fig, ax = plt.subplots(figsize=(14.5, 8.4), dpi=160)
    x_positions = list(range(len(pivot)))
    bottoms = [0.0] * len(pivot)

    for wrong_type in value_columns:
        values = [float(value) for value in pivot[wrong_type]]
        bars = ax.bar(
            x_positions,
            values,
            bottom=bottoms,
            color=TYPE_COLORS[wrong_type],
            edgecolor="#FFFFFF",
            linewidth=0.9,
            label=TYPE_LABELS[wrong_type],
        )
        for index, (bar, value, bottom) in enumerate(zip(bars, values, bottoms, strict=False)):
            if percentage:
                show_label = value >= 0.08
                label = f"{value * 100:.0f}%"
            else:
                show_label = value >= 6
                label = f"{int(value)}"
            if show_label:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom + value / 2,
                    label,
                    ha="center",
                    va="center",
                    color="#FFFFFF",
                    fontsize=10,
                    fontweight="bold",
                )
        bottoms = [bottom + value for bottom, value in zip(bottoms, values, strict=False)]

    labels = [
        f"{row.model_label}\n오답 n={int(row.wrong_count)}"
        for row in pivot.itertuples(index=False)
    ]
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    if percentage:
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    else:
        ax.set_ylim(0, max(bottoms) * 1.12)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
    )
    fig.subplots_adjust(bottom=0.31, left=0.08, right=0.98, top=0.9)
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    pd, plt = import_libs()
    set_plot_style(plt)

    data = load_summary(pd, args.wrong_type_summary)
    args.charts_dir.mkdir(parents=True, exist_ok=True)

    ratio_pivot = pivot_for(data, "wrong_type_ratio_of_wrong")
    count_pivot = pivot_for(data, "wrong_type_count")
    value_columns = [wrong_type for wrong_type in TYPE_ORDER if wrong_type in ratio_pivot]

    draw_stacked_bar(
        plt,
        ratio_pivot,
        value_columns,
        title="모델별 No-Tool 오답 유형 비율",
        ylabel="No-Tool 오답 중 비율",
        filename=args.charts_dir / "tools_no_wrong_type_distribution_ratio.png",
        percentage=True,
    )
    draw_stacked_bar(
        plt,
        count_pivot,
        value_columns,
        title="모델별 No-Tool 오답 유형 개수",
        ylabel="오답 개수",
        filename=args.charts_dir / "tools_no_wrong_type_distribution_count.png",
        percentage=False,
    )

    print(f"wrote {args.charts_dir / 'tools_no_wrong_type_distribution_ratio.png'}")
    print(f"wrote {args.charts_dir / 'tools_no_wrong_type_distribution_count.png'}")


if __name__ == "__main__":
    main()
