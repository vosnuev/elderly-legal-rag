from __future__ import annotations

import argparse
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "docs" / "benchmark" / "artifacts"


def default_results_dir() -> Path:
    candidates = [
        ROOT_DIR / "docs" / "benchmark" / "results",
        ROOT_DIR / "backend" / "tests" / "benchmark" / "artifacts",
        ROOT_DIR / "backend" / "results",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


DEFAULT_RESULTS_DIR = default_results_dir()

NUMERIC_COLUMNS = [
    "input_price_per_1m",
    "output_price_per_1m",
    "input_tokens",
    "output_tokens",
    "used_tokens",
    "input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
    "context_length",
    "max_completion_tokens",
    "latency_ms",
]

ROUTING_GROUP_COLUMNS = ["model_id", "primary_provider_slug", "source_file"]
TRUTHY_VALUES = {"true", "1", "yes", "y"}

MODEL_COLORS = {
    "openai/gpt-oss-120b": "#2563EB",
    "deepseek/deepseek-v4-flash": "#16A34A",
    "deepseek/deepseek-v4-pro": "#F97316",
}

DISPLAY_ORDER = [
    ("openai/gpt-oss-120b", "cerebras"),
    ("deepseek/deepseek-v4-flash", "deepinfra"),
    ("deepseek/deepseek-v4-flash", "deepseek"),
    ("deepseek/deepseek-v4-flash", "siliconflow"),
    ("deepseek/deepseek-v4-flash", "gmicloud"),
    ("deepseek/deepseek-v4-pro", "streamlake"),
    ("deepseek/deepseek-v4-pro", "deepseek"),
    ("deepseek/deepseek-v4-pro", "gmicloud"),
    ("deepseek/deepseek-v4-pro", "alibaba"),
    ("deepseek/deepseek-v4-pro", "novita"),
    ("deepseek/deepseek-v4-pro", "siliconflow"),
    ("deepseek/deepseek-v4-pro", "atlas-cloud"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze no_tool benchmark CSV files by model/provider."
    )
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--include-qwen",
        action="store_true",
        help="Include qwen files if they exist. Default excludes them because Qwen was dropped.",
    )
    parser.add_argument(
        "--include-nonstrict-routing",
        action="store_true",
        help=(
            "Include providers that do not pass routing validation. Default only compares "
            "providers with allow_fallbacks=false and confirmed successful actual_provider routing."
        ),
    )
    return parser.parse_args()


def import_analysis_libs():
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise SystemExit(
            "pandas/numpy are required. Example:\n"
            "uv run --with pandas --with numpy --with matplotlib "
            "python docs/benchmark/analyze_no_tool_results.py"
        ) from exc

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None

    return pd, np, plt


def result_files(results_dir: Path, include_qwen: bool) -> list[Path]:
    combined = results_dir / "no_tool_combined_results.csv"
    if combined.exists():
        return [combined]

    files: list[Path] = []
    for path in sorted(results_dir.glob("*.csv")):
        name = path.name.lower()
        if "summary" in name:
            continue
        if not include_qwen and "qwen" in name:
            continue
        if "smoke" in name or "raw" in name:
            continue
        files.append(path)
    return files


def extract_query_text(value: object) -> str:
    text = "" if value is None else str(value)
    for line in text.splitlines():
        if line.startswith("query:"):
            return line.removeprefix("query:").strip()
    return ""


def load_results(pd, results_dir: Path, include_qwen: bool):
    frames = []
    for path in result_files(results_dir, include_qwen):
        frame = pd.read_csv(path)
        frame = frame.drop(
            columns=[
                column
                for column in [
                    "is_success",
                    "allow_fallbacks_bool",
                    "actual_provider_missing",
                    "actual_provider_mismatch",
                    "success_actual_provider_missing",
                    "success_actual_provider_mismatch",
                    "provider_key",
                    "query_text",
                    "routing_eligible",
                    "routing_issue",
                ]
                if column in frame.columns
            ]
        )
        if "source_file" not in frame.columns:
            frame["source_file"] = path.name
        frames.append(frame)

    if not frames:
        raise SystemExit(f"No benchmark CSV files found in {results_dir}")

    data = pd.concat(frames, ignore_index=True)
    for column in [
        "status",
        "model_id",
        "primary_provider_slug",
        "actual_provider",
        "allow_fallbacks",
        "query_reference",
    ]:
        if column not in data.columns:
            data[column] = ""

    for column in NUMERIC_COLUMNS:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    data["status"] = data["status"].fillna("").astype(str).str.strip()
    data["model_id"] = data["model_id"].fillna("").astype(str).str.strip()
    data["primary_provider_slug"] = (
        data["primary_provider_slug"].fillna("").astype(str).str.strip()
    )
    data["actual_provider"] = data["actual_provider"].fillna("").astype(str).str.strip()
    data["allow_fallbacks"] = data["allow_fallbacks"].fillna("").astype(str).str.strip()

    data["is_success"] = data["status"].eq("success")
    data["allow_fallbacks_bool"] = (
        data["allow_fallbacks"].str.lower().isin(TRUTHY_VALUES)
    )
    data["actual_provider_missing"] = data["actual_provider"].eq("")
    data["actual_provider_mismatch"] = (
        ~data["actual_provider_missing"]
        & data["actual_provider"].ne(data["primary_provider_slug"])
    )
    data["success_actual_provider_missing"] = (
        data["is_success"] & data["actual_provider_missing"]
    )
    data["success_actual_provider_mismatch"] = (
        data["is_success"] & data["actual_provider_mismatch"]
    )
    data["provider_key"] = data["model_id"].astype(str) + " / " + data[
        "primary_provider_slug"
    ].astype(str)
    data["query_text"] = data["query_reference"].map(extract_query_text)
    return data


def unique_join(series) -> str:
    values = sorted(
        {
            str(value).strip()
            for value in series.dropna()
            if str(value).strip() and str(value).strip().lower() != "nan"
        }
    )
    return ", ".join(values)


def routing_issue(row) -> str:
    issues = []
    if int(row.fallback_true_count) > 0:
        issues.append("allow_fallbacks=true")
    if int(row.success_actual_provider_missing_count) > 0:
        issues.append("actual_provider missing on success")
    if int(row.success_actual_provider_mismatch_count) > 0:
        issues.append("actual_provider mismatch on success")
    return "; ".join(issues) if issues else "ok"


def build_routing_report(data):
    report = (
        data.groupby(ROUTING_GROUP_COLUMNS)
        .agg(
            row_count=("testcase_id", "count"),
            success_count=("is_success", "sum"),
            failed_count=("is_success", lambda s: int((~s).sum())),
            allow_fallbacks_values=("allow_fallbacks", unique_join),
            actual_provider_values=("actual_provider", unique_join),
            fallback_true_count=("allow_fallbacks_bool", "sum"),
            actual_provider_missing_count=("actual_provider_missing", "sum"),
            actual_provider_mismatch_count=("actual_provider_mismatch", "sum"),
            success_actual_provider_missing_count=(
                "success_actual_provider_missing",
                "sum",
            ),
            success_actual_provider_mismatch_count=(
                "success_actual_provider_mismatch",
                "sum",
            ),
        )
        .reset_index()
    )
    report["routing_eligible"] = (
        report["fallback_true_count"].eq(0)
        & report["success_actual_provider_missing_count"].eq(0)
        & report["success_actual_provider_mismatch_count"].eq(0)
    )
    report["routing_issue"] = report.apply(routing_issue, axis=1)
    return report.sort_values(ROUTING_GROUP_COLUMNS)


def attach_routing_eligibility(data, routing_report):
    return data.merge(
        routing_report[ROUTING_GROUP_COLUMNS + ["routing_eligible", "routing_issue"]],
        on=ROUTING_GROUP_COLUMNS,
        how="left",
    )


def percentile(np, value: float):
    def inner(series):
        clean = series.dropna()
        if clean.empty:
            return float("nan")
        return float(np.percentile(clean, value))

    inner.__name__ = f"p{int(value)}"
    return inner


def build_provider_summary(pd, np, data):
    group_cols = ["model_id", "primary_provider_slug", "source_file"]
    all_rows = (
        data.groupby(group_cols)
        .agg(
            row_count=("testcase_id", "count"),
            success_count=("is_success", "sum"),
            failed_count=("is_success", lambda s: int((~s).sum())),
        )
        .reset_index()
    )

    success = data[data["is_success"]].copy()
    metrics = (
        success.groupby(group_cols)
        .agg(
            avg_input_tokens=("input_tokens", "mean"),
            avg_output_tokens=("output_tokens", "mean"),
            avg_used_tokens=("used_tokens", "mean"),
            median_used_tokens=("used_tokens", "median"),
            p95_used_tokens=("used_tokens", percentile(np, 95)),
            avg_total_cost_usd=("total_cost_usd", "mean"),
            sum_total_cost_usd=("total_cost_usd", "sum"),
            avg_latency_ms=("latency_ms", "mean"),
            median_latency_ms=("latency_ms", "median"),
            p95_latency_ms=("latency_ms", percentile(np, 95)),
        )
        .reset_index()
    )

    summary = all_rows.merge(metrics, on=group_cols, how="left")
    summary["success_rate"] = summary["success_count"] / summary["row_count"] * 100
    return summary.sort_values(
        ["model_id", "avg_total_cost_usd", "avg_latency_ms"], na_position="last"
    )


def build_question_summary(pd, data):
    success = data[data["is_success"]].copy()
    summary = (
        success.groupby(["testcase_id", "query_text"])
        .agg(
            provider_count=("provider_key", "nunique"),
            avg_input_tokens=("input_tokens", "mean"),
            avg_output_tokens=("output_tokens", "mean"),
            avg_used_tokens=("used_tokens", "mean"),
            avg_total_cost_usd=("total_cost_usd", "mean"),
            avg_latency_ms=("latency_ms", "mean"),
            max_latency_ms=("latency_ms", "max"),
        )
        .reset_index()
    )

    if not success.empty:
        fastest_idx = success.groupby("testcase_id")["latency_ms"].idxmin()
        cheapest_idx = success.groupby("testcase_id")["total_cost_usd"].idxmin()
        fastest = success.loc[fastest_idx, ["testcase_id", "provider_key"]].rename(
            columns={"provider_key": "fastest_provider"}
        )
        cheapest = success.loc[cheapest_idx, ["testcase_id", "provider_key"]].rename(
            columns={"provider_key": "cheapest_provider"}
        )
        summary = summary.merge(fastest, on="testcase_id", how="left")
        summary = summary.merge(cheapest, on="testcase_id", how="left")

    return summary.sort_values("testcase_id")


def build_segment_summary(data):
    success = data[data["is_success"]].copy()
    return (
        success.groupby(["model_id", "primary_provider_slug", "batch", "difficulty"])
        .agg(
            row_count=("testcase_id", "count"),
            avg_used_tokens=("used_tokens", "mean"),
            avg_total_cost_usd=("total_cost_usd", "mean"),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .reset_index()
        .sort_values(["model_id", "primary_provider_slug", "batch", "difficulty"])
    )


def short_model(model_id: object) -> str:
    text = "" if model_id is None else str(model_id)
    if "/" in text:
        return text.split("/", 1)[1]
    return text


def model_color(model_id: object) -> str:
    return MODEL_COLORS.get(str(model_id), "#6B7280")


def add_display_columns(frame):
    order_map = {
        (model_id, provider): index + 1
        for index, (model_id, provider) in enumerate(DISPLAY_ORDER)
    }
    frame = frame.copy()
    frame["display_id"] = [
        order_map.get((row.model_id, row.primary_provider_slug), index + 1)
        for index, row in enumerate(frame.itertuples(index=False))
    ]
    frame["model_short"] = frame["model_id"].map(short_model)
    frame["model_color"] = frame["model_id"].map(model_color)
    return frame


def apply_provider_axis_labels(ax, ordered, *, y_first: float = -0.08) -> None:
    positions = list(range(len(ordered)))
    ax.set_xticks(positions)
    ax.set_xticklabels([""] * len(ordered))
    transform = ax.get_xaxis_transform()
    for position, row in enumerate(ordered.itertuples(index=False)):
        ax.text(
            position,
            y_first,
            f"#{int(row.display_id)}\n{row.primary_provider_slug}",
            transform=transform,
            ha="center",
            va="top",
            fontsize=11,
            color="#111827",
            linespacing=1.12,
        )


def format_chart_value(column: str, value: float) -> str:
    if column == "avg_total_cost_usd":
        return f"${value:.6f}"
    if column == "avg_latency_ms":
        return f"{value / 1000:.1f}s"
    if column == "avg_used_tokens":
        return f"{value:,.0f}"
    if column in {"avg_input_tokens", "avg_output_tokens"}:
        return f"{value:,.0f}"
    return f"{value:.2f}"


def add_bar_labels(ax, bars, values, column: str) -> None:
    ymin, ymax = ax.get_ylim()
    offset = (ymax - ymin) * 0.015
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            format_chart_value(column, float(value)),
            ha="center",
            va="bottom",
            fontsize=10,
            color="#111827",
            fontweight="bold",
        )


def save_charts(plt, provider_summary, data, output_dir: Path) -> None:
    if plt is None:
        print("matplotlib is not installed; skipped chart generation.")
        return
    from matplotlib.patches import Patch

    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.edgecolor": "#D1D5DB",
            "axes.labelcolor": "#111827",
            "axes.titleweight": "bold",
            "axes.titlesize": 17,
            "axes.labelsize": 13,
            "legend.fontsize": 11,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
        }
    )

    charts_dir = output_dir.parent / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    chart_data = add_display_columns(provider_summary)
    legend_handles = [
        Patch(facecolor=color, edgecolor="#111827", label=short_model(model_id))
        for model_id, color in MODEL_COLORS.items()
        if model_id in set(chart_data["model_id"])
    ]

    def save_bar(
        column: str,
        title: str,
        ylabel: str,
        filename: str,
        *,
        zoom_y: bool = False,
        zoom_min_padding: float = 80,
        line_overlay: bool = False,
    ) -> None:
        ordered = chart_data.sort_values(column)
        fig, ax = plt.subplots(figsize=(15, 8))
        colors = list(ordered["model_color"])
        bars = ax.bar(
            range(len(ordered)),
            ordered[column],
            color=colors,
            edgecolor="#111827",
            linewidth=0.7,
            alpha=0.9,
        )
        if line_overlay:
            ax.plot(
                range(len(ordered)),
                ordered[column],
                color="#111827",
                linewidth=2,
                marker="o",
                markersize=5,
                markerfacecolor="#FFFFFF",
                markeredgecolor="#111827",
                markeredgewidth=1.2,
                zorder=4,
            )
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(
            handles=legend_handles,
            title="model",
            loc="upper left",
            frameon=True,
            facecolor="#FFFFFF",
            edgecolor="#D1D5DB",
        )
        if zoom_y:
            ymin = float(ordered[column].min())
            ymax = float(ordered[column].max())
            padding = max((ymax - ymin) * 0.16, zoom_min_padding)
            ax.set_ylim(max(0, ymin - padding), ymax + padding)
            ax.text(
                0.99,
                0.98,
                "zoomed y-axis",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=10,
                color="#6B7280",
            )
        else:
            ax.set_ylim(0, float(ordered[column].max()) * 1.16)
        add_bar_labels(ax, bars, list(ordered[column]), column)
        apply_provider_axis_labels(ax, ordered)
        fig.subplots_adjust(bottom=0.22)
        fig.tight_layout()
        fig.savefig(charts_dir / filename, dpi=160)
        plt.close(fig)

    save_bar(
        "avg_total_cost_usd",
        "Average Cost Per Successful Question",
        "USD",
        "avg_cost_per_question.png",
        line_overlay=True,
    )
    save_bar(
        "avg_latency_ms",
        "Average Latency Per Successful Question",
        "milliseconds",
        "avg_latency_ms.png",
        line_overlay=True,
    )
    save_bar(
        "avg_input_tokens",
        "Average Input Tokens Per Successful Question",
        "tokens",
        "avg_input_tokens.png",
        zoom_y=True,
        zoom_min_padding=4,
        line_overlay=True,
    )
    save_bar(
        "avg_output_tokens",
        "Average Output Tokens Per Successful Question",
        "tokens",
        "avg_output_tokens.png",
        line_overlay=True,
    )
    save_bar(
        "avg_used_tokens",
        "Average Used Tokens Per Successful Question",
        "tokens",
        "avg_used_tokens.png",
        zoom_y=True,
        line_overlay=True,
    )

    scatter_data = chart_data.sort_values("display_id")
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.scatter(
        scatter_data["avg_total_cost_usd"],
        scatter_data["avg_latency_ms"],
        s=130,
        c=list(scatter_data["model_color"]),
        edgecolor="#111827",
        linewidth=0.8,
        alpha=0.92,
        zorder=3,
    )
    label_offsets = [
        (14, 12),
        (16, -18),
        (16, 14),
        (-78, 12),
        (-80, -18),
        (16, 16),
        (-86, 12),
        (16, -20),
        (-78, -18),
        (14, 18),
        (-86, 16),
        (14, -20),
    ]
    for index, row in enumerate(scatter_data.itertuples(index=False)):
        offset = label_offsets[index % len(label_offsets)]
        ax.annotate(
            f"#{int(row.display_id)} {row.primary_provider_slug}",
            (row.avg_total_cost_usd, row.avg_latency_ms),
            xytext=offset,
            textcoords="offset points",
            fontsize=10,
            color="#111827",
            fontweight="bold",
            arrowprops={"arrowstyle": "-", "color": "#9CA3AF", "lw": 0.6},
        )
    ax.set_title("Provider Cost vs Latency")
    ax.set_xlabel("Average cost per question (USD)")
    ax.set_ylabel("Average latency (ms)")
    ax.grid(color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(
        handles=legend_handles,
        title="model",
        loc="upper left",
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#D1D5DB",
    )
    x_min = float(scatter_data["avg_total_cost_usd"].min())
    x_max = float(scatter_data["avg_total_cost_usd"].max())
    y_min = float(scatter_data["avg_latency_ms"].min())
    y_max = float(scatter_data["avg_latency_ms"].max())
    ax.set_xlim(max(0, x_min - (x_max - x_min) * 0.12), x_max + (x_max - x_min) * 0.18)
    ax.set_ylim(max(0, y_min - (y_max - y_min) * 0.12), y_max + (y_max - y_min) * 0.14)
    fig.tight_layout()
    fig.savefig(charts_dir / "cost_vs_latency_scatter.png", dpi=160)
    plt.close(fig)

    success = data[data["is_success"]].copy()
    success = success.merge(
        chart_data[["model_id", "primary_provider_slug", "display_id", "model_short", "model_color"]],
        on=["model_id", "primary_provider_slug"],
        how="left",
    )
    box_order = chart_data.sort_values("display_id")
    labels = [
        (row.model_id, row.primary_provider_slug)
        for row in box_order.itertuples(index=False)
    ]
    box_values = [
        success.loc[
            success["model_id"].eq(model_id)
            & success["primary_provider_slug"].eq(provider),
            "latency_ms",
        ].dropna()
        for model_id, provider in labels
    ]
    positions = list(range(len(box_order)))
    fig, ax = plt.subplots(figsize=(15, 8))
    box = ax.boxplot(
        box_values,
        positions=positions,
        patch_artist=True,
        showfliers=False,
        widths=0.62,
    )
    for patch, row in zip(box["boxes"], box_order.itertuples(index=False)):
        patch.set_facecolor(row.model_color)
        patch.set_alpha(0.28)
        patch.set_edgecolor(row.model_color)
        patch.set_linewidth(1.2)
    for median in box["medians"]:
        median.set_color("#111827")
        median.set_linewidth(1.4)
    for whisker in box["whiskers"]:
        whisker.set_color("#6B7280")
    for cap in box["caps"]:
        cap.set_color("#6B7280")
    medians = [values.median() if len(values) else 0 for values in box_values]
    ymin, ymax = ax.get_ylim()
    offset = (ymax - ymin) * 0.018
    for position, median, row in zip(positions, medians, box_order.itertuples(index=False)):
        ax.text(
            position,
            median + offset,
            f"{median / 1000:.1f}s",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#111827",
            fontweight="bold",
        )
    ax.set_title("Latency Distribution By Provider")
    ax.set_ylabel("milliseconds")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(
        handles=legend_handles,
        title="model",
        loc="upper left",
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#D1D5DB",
    )
    apply_provider_axis_labels(ax, box_order, y_first=-0.08)
    fig.subplots_adjust(bottom=0.22)
    fig.tight_layout()
    fig.savefig(charts_dir / "latency_distribution_boxplot.png", dpi=160)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    pd, np, plt = import_analysis_libs()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_data = load_results(pd, args.results_dir, args.include_qwen)
    routing_report = build_routing_report(all_data)
    data = attach_routing_eligibility(all_data, routing_report)
    analysis_data = (
        data.copy()
        if args.include_nonstrict_routing
        else data[data["routing_eligible"]].copy()
    )
    if analysis_data.empty:
        raise SystemExit(
            "No rows left after routing validation. Use --include-nonstrict-routing "
            "to inspect non-strict data."
        )

    provider_summary = build_provider_summary(pd, np, analysis_data)
    question_summary = build_question_summary(pd, analysis_data)
    segment_summary = build_segment_summary(analysis_data)
    failures = data[~data["is_success"]].copy()
    excluded_routing = routing_report[~routing_report["routing_eligible"]].copy()

    data.to_csv(args.output_dir / "no_tool_all_results.csv", index=False)
    analysis_data.to_csv(args.output_dir / "no_tool_combined_results.csv", index=False)
    routing_report.to_csv(args.output_dir / "no_tool_routing_report.csv", index=False)
    excluded_routing.to_csv(
        args.output_dir / "no_tool_excluded_routing_report.csv", index=False
    )
    provider_summary.to_csv(args.output_dir / "no_tool_provider_summary.csv", index=False)
    question_summary.to_csv(args.output_dir / "no_tool_question_summary.csv", index=False)
    segment_summary.to_csv(args.output_dir / "no_tool_segment_summary.csv", index=False)
    failures.to_csv(args.output_dir / "no_tool_failure_report.csv", index=False)
    save_charts(plt, provider_summary, analysis_data, args.output_dir)

    print(f"wrote artifacts to {args.output_dir}")
    if not excluded_routing.empty and not args.include_nonstrict_routing:
        print("excluded non-strict routing providers:")
        print(excluded_routing.to_string(index=False))
    print(provider_summary.to_string(index=False))


if __name__ == "__main__":
    main()
