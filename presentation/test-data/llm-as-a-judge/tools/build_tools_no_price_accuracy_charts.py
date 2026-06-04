from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TOOLS_NO_DIR = REPO_ROOT / "presentation" / "test-data" / "llm-as-a-judge" / "artifacts" / "tools-no"
RAW_RESULTS_DIR = REPO_ROOT / "presentation" / "test-data" / "no-tool-benchmark" / "raw-results"
DEFAULT_JUDGE_SUMMARY = TOOLS_NO_DIR / "llm_judge_model_summary.csv"
DEFAULT_OUTPUT_SUMMARY = TOOLS_NO_DIR / "tools_no_price_accuracy_summary.csv"
DEFAULT_CHARTS_DIR = TOOLS_NO_DIR / "charts"

NORMALIZED_QUESTION_COUNT = 360

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

MODEL_COLORS = {
    "deepseek/deepseek-v4-flash": "#16A34A",
    "deepseek/deepseek-v4-pro": "#F97316",
    "openai/gpt-oss-120b": "#2563EB",
    "qwen/qwen3.7-plus": "#7C3AED",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build no-tool price/accuracy charts from OpenRouter raw costs and "
            "LLM-as-a-judge accuracy."
        )
    )
    parser.add_argument("--raw-results-dir", type=Path, default=RAW_RESULTS_DIR)
    parser.add_argument("--judge-summary", type=Path, default=DEFAULT_JUDGE_SUMMARY)
    parser.add_argument("--output-summary", type=Path, default=DEFAULT_OUTPUT_SUMMARY)
    parser.add_argument("--charts-dir", type=Path, default=DEFAULT_CHARTS_DIR)
    parser.add_argument("--normalized-questions", type=int, default=NORMALIZED_QUESTION_COUNT)
    return parser.parse_args()


def import_libs():
    try:
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "pandas/numpy/matplotlib are required. Example:\n"
            "cd backend && uv run --with pandas --with numpy --with matplotlib "
            "python ../presentation/test-data/llm-as-a-judge/tools/"
            "build_tools_no_price_accuracy_charts.py"
        ) from exc

    return pd, np, plt


def display_model(model_id: str) -> str:
    return MODEL_LABELS.get(model_id, model_id.split("/", 1)[-1] if "/" in model_id else model_id)


def display_label(model_id: str, provider: str) -> str:
    model = display_model(model_id)
    return f"{model}\n{provider}" if provider else model


def short_label(model_id: str, provider: str) -> str:
    model = display_model(model_id)
    return f"{model} / {provider}" if provider else model


def sample_note(row, normalized_questions: int = NORMALIZED_QUESTION_COUNT) -> str:
    parts = []
    if int(row.raw_questions) < normalized_questions:
        parts.append(f"cost n={int(row.raw_questions)} -> {normalized_questions}")
    if row.judge_status == "judge_complete" and int(row.judge_questions) < normalized_questions:
        parts.append(f"judge n={int(row.judge_questions)}")
    if row.judge_status != "judge_complete":
        parts.append("judge pending")
    return ", ".join(parts)


def read_raw_costs(pd, raw_results_dir: Path, normalized_questions: int):
    frames = []
    for path in sorted(raw_results_dir.glob("*.csv")):
        if "smoke" in path.name.lower():
            continue
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        frame["source_file"] = path.name
        frames.append(frame)

    if not frames:
        raise SystemExit(f"No raw result CSV files found in {raw_results_dir}")

    raw = pd.concat(frames, ignore_index=True)
    for column in [
        "input_tokens",
        "output_tokens",
        "used_tokens",
        "input_cost_usd",
        "output_cost_usd",
        "total_cost_usd",
        "latency_ms",
    ]:
        raw[column] = pd.to_numeric(raw.get(column), errors="coerce")

    raw["is_success"] = raw["status"].fillna("").astype(str).eq("success")
    group_cols = ["source_file", "model_id", "primary_provider_slug"]

    counts = (
        raw.groupby(group_cols)
        .agg(
            raw_questions=("testcase_id", "count"),
            raw_success_count=("is_success", "sum"),
            raw_failed_count=("is_success", lambda values: int((~values).sum())),
        )
        .reset_index()
    )

    success = raw[raw["is_success"]].copy()
    metrics = (
        success.groupby(group_cols)
        .agg(
            observed_total_cost_usd=("total_cost_usd", "sum"),
            avg_total_cost_usd=("total_cost_usd", "mean"),
            avg_input_cost_usd=("input_cost_usd", "mean"),
            avg_output_cost_usd=("output_cost_usd", "mean"),
            avg_input_tokens=("input_tokens", "mean"),
            avg_output_tokens=("output_tokens", "mean"),
            avg_used_tokens=("used_tokens", "mean"),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .reset_index()
    )

    summary = counts.merge(metrics, on=group_cols, how="left")
    summary["projected_total_cost_usd"] = summary["avg_total_cost_usd"] * normalized_questions
    summary["cost_projection_basis"] = summary.apply(
        lambda row: (
            "observed full set"
            if int(row.raw_questions) >= normalized_questions
            else f"projected from {int(row.raw_questions)} observed questions"
        ),
        axis=1,
    )
    summary = summary.rename(columns={"primary_provider_slug": "provider"})
    return summary


def read_judge_summary(pd, judge_summary_path: Path):
    if not judge_summary_path.exists():
        return pd.DataFrame(
            columns=[
                "source_file",
                "model_id",
                "provider",
                "judge_questions",
                "correct_count",
                "wrong_count",
                "accuracy",
            ]
        )

    judge = pd.read_csv(judge_summary_path)
    judge = judge.rename(columns={"total_questions": "judge_questions"})
    for column in ["judge_questions", "correct_count", "wrong_count", "accuracy"]:
        judge[column] = pd.to_numeric(judge.get(column), errors="coerce")
    return judge[
        [
            "source_file",
            "model_id",
            "provider",
            "judge_questions",
            "correct_count",
            "wrong_count",
            "accuracy",
        ]
    ]


def build_summary(pd, raw_costs, judge_summary, normalized_questions: int):
    summary = raw_costs.merge(
        judge_summary,
        on=["source_file", "model_id", "provider"],
        how="left",
    )
    summary["judge_status"] = summary["accuracy"].apply(
        lambda value: "judge_complete" if pd.notna(value) else "judge_pending"
    )
    summary["normalized_question_count"] = normalized_questions
    summary["projected_correct_count"] = summary["accuracy"] * normalized_questions
    summary["projected_wrong_count"] = normalized_questions - summary["projected_correct_count"]
    summary["projected_cost_per_correct_usd"] = (
        summary["projected_total_cost_usd"] / summary["projected_correct_count"]
    )
    summary["accuracy_percent"] = summary["accuracy"] * 100
    summary["label"] = [
        display_label(model_id, provider)
        for model_id, provider in zip(summary["model_id"], summary["provider"], strict=False)
    ]
    summary["short_label"] = [
        short_label(model_id, provider)
        for model_id, provider in zip(summary["model_id"], summary["provider"], strict=False)
    ]
    summary["color"] = summary["model_id"].map(lambda value: MODEL_COLORS.get(value, "#6B7280"))
    summary["sort_order"] = summary["source_file"].map(lambda value: MODEL_ORDER.get(value, 999))
    summary["coverage_note"] = summary.apply(
        lambda row: (
            f"judge complete: {int(row.judge_questions)} questions"
            if row.judge_status == "judge_complete"
            else f"raw cost only: {int(row.raw_questions)} questions; accuracy pending"
        ),
        axis=1,
    )
    return summary.sort_values(["sort_order", "projected_total_cost_usd"]).reset_index(drop=True)


def set_plot_style(plt) -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "axes.edgecolor": "#D1D5DB",
            "axes.labelcolor": "#111827",
            "axes.titleweight": "bold",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 11,
            "font.size": 12,
        }
    )


def save_price_vs_accuracy_chart(plt, summary, charts_dir: Path) -> None:
    complete = summary[summary["judge_status"].eq("judge_complete")].copy()
    pending = summary[summary["judge_status"].ne("judge_complete")].copy()

    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=160)
    ax.grid(True, axis="both", color="#E5E7EB", linewidth=1, alpha=0.9)
    ax.set_axisbelow(True)

    ax.scatter(
        complete["projected_total_cost_usd"],
        complete["accuracy_percent"],
        s=220,
        c=complete["color"],
        edgecolors="#111827",
        linewidths=1.2,
        zorder=3,
    )

    for row in complete.itertuples(index=False):
        note = sample_note(row)
        note_line = f"\n{note}" if note else ""
        ax.annotate(
            (
                f"{display_model(row.model_id)}\n"
                f"{row.accuracy_percent:.1f}% / ${row.projected_total_cost_usd:.3f}"
                f"{note_line}"
            ),
            (row.projected_total_cost_usd, row.accuracy_percent),
            textcoords="offset points",
            xytext=(10, 10),
            ha="left",
            va="bottom",
            fontsize=10,
            color="#111827",
        )

    ax.set_title(
        "No-Tool Benchmark: OpenRouter Spend vs LLM-as-Judge Accuracy\n"
        "Question answered: how much performance do we buy for this spend?"
    )
    ax.set_xlabel("Projected OpenRouter cost for 360 questions, based on actual token usage (USD)")
    ax.set_ylabel("LLM-as-Judge accuracy from judged questions (%)")
    ax.set_ylim(55, 80)
    xmax_values = list(complete["projected_total_cost_usd"].dropna())
    if not pending.empty:
        xmax_values.extend(list(pending["projected_total_cost_usd"].dropna()))
    xmax = max(xmax_values) if xmax_values else 1
    ax.set_xlim(0, xmax * 1.18)

    if not pending.empty:
        for row in pending.itertuples(index=False):
            ax.axvline(
                row.projected_total_cost_usd,
                color=row.color,
                linestyle="--",
                linewidth=2,
                alpha=0.75,
                zorder=1,
            )
            ax.text(
                row.projected_total_cost_usd,
                78.8,
                f"{display_model(row.model_id)} cost only\n${row.projected_total_cost_usd:.3f} / judge pending",
                ha="right",
                va="top",
                fontsize=10,
                color="#111827",
                bbox={
                    "boxstyle": "round,pad=0.35",
                    "facecolor": "#F5F3FF",
                    "edgecolor": row.color,
                },
            )
        lines = [
            (
                f"{display_model(row.model_id)} / {row.provider}: "
                f"${row.projected_total_cost_usd:.3f} projected for 360 Qs "
                f"from {int(row.raw_questions)} raw Qs; judge accuracy pending"
            )
            for row in pending.itertuples(index=False)
        ]
        ax.text(
            0.02,
            0.03,
            "\n".join(lines),
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=10,
            color="#374151",
            bbox={
                "boxstyle": "round,pad=0.45",
                "facecolor": "#F9FAFB",
                "edgecolor": "#D1D5DB",
            },
        )

    fig.tight_layout()
    fig.savefig(charts_dir / "tools_no_price_vs_llm_judge_accuracy.png", bbox_inches="tight")
    plt.close(fig)


def save_cost_per_correct_chart(plt, summary, charts_dir: Path) -> None:
    complete = summary[summary["judge_status"].eq("judge_complete")].copy()
    complete = complete.sort_values("projected_cost_per_correct_usd")
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=160)

    bars = ax.barh(
        complete["label"],
        complete["projected_cost_per_correct_usd"],
        color=complete["color"],
        edgecolor="#111827",
        linewidth=0.8,
    )
    ax.grid(True, axis="x", color="#E5E7EB", linewidth=1)
    ax.set_axisbelow(True)
    ax.set_title(
        "No-Tool Benchmark: Cost per Correct Answer\n"
        "360-question spend projection divided by LLM-as-Judge correctness"
    )
    ax.set_xlabel("Projected USD per correct answer on a 360-question run")
    ax.set_ylabel("")

    for bar, row in zip(bars, complete.itertuples(index=False), strict=False):
        note = sample_note(row)
        value = row.projected_cost_per_correct_usd
        label = f"${value:.4f}" + (f"\n{note}" if note else "")
        ax.text(
            value + max(complete["projected_cost_per_correct_usd"]) * 0.018,
            bar.get_y() + bar.get_height() / 2,
            label,
            ha="left",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="#111827",
        )

    fig.tight_layout()
    fig.savefig(charts_dir / "tools_no_cost_per_correct_answer.png", bbox_inches="tight")
    plt.close(fig)


def save_cost_projection_chart(plt, summary, charts_dir: Path) -> None:
    ordered = summary.sort_values("projected_total_cost_usd").copy()
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=160)
    x = range(len(ordered))
    colors = list(ordered["color"])

    bars = ax.bar(
        x,
        ordered["projected_total_cost_usd"],
        color=colors,
        edgecolor="#111827",
        linewidth=0.8,
    )
    ax.grid(True, axis="y", color="#E5E7EB", linewidth=1)
    ax.set_axisbelow(True)
    ax.set_title(
        "No-Tool Benchmark: OpenRouter Cost Projected to 360 Questions\n"
        "Partial raw runs are normalized by observed average token cost"
    )
    ax.set_ylabel("Projected cost for 360 questions (USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(list(ordered["label"]), rotation=0, ha="center")

    for bar, row in zip(bars, ordered.itertuples(index=False), strict=False):
        label = f"${row.projected_total_cost_usd:.3f}"
        note = sample_note(row)
        if note:
            label += f"\n{note}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            row.projected_total_cost_usd + max(ordered["projected_total_cost_usd"]) * 0.018,
            label,
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#111827",
        )

    fig.tight_layout()
    fig.savefig(charts_dir / "tools_no_360_question_cost_projection.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    pd, _np, plt = import_libs()
    set_plot_style(plt)

    args.charts_dir.mkdir(parents=True, exist_ok=True)
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)

    raw_costs = read_raw_costs(pd, args.raw_results_dir, args.normalized_questions)
    judge_summary = read_judge_summary(pd, args.judge_summary)
    summary = build_summary(pd, raw_costs, judge_summary, args.normalized_questions)
    summary.to_csv(args.output_summary, index=False, encoding="utf-8-sig")

    save_price_vs_accuracy_chart(plt, summary, args.charts_dir)
    save_cost_per_correct_chart(plt, summary, args.charts_dir)
    save_cost_projection_chart(plt, summary, args.charts_dir)

    print(f"wrote summary: {args.output_summary}")
    print(f"wrote charts: {args.charts_dir}")


if __name__ == "__main__":
    main()
