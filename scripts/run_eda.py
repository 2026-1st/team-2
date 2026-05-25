#!/usr/bin/env python3
"""Generate EDA figures for the processed team-feature dataset."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Avoid matplotlib trying to use GUI backends or write to home cache dirs in
# sandboxed/macOS setups. These must be set before importing pyplot.
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/team2-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/team2-cache")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from team2_surrender.config import load_settings  # noqa: E402
from team2_surrender.modeling import FEATURE_COLUMNS, TARGET_COLUMN  # noqa: E402
from team2_surrender.storage import atomic_write_json, utc_now_iso  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--figure-dir", type=Path, default=None)
    parser.add_argument("--metrics-csv", type=Path, default=None)
    return parser.parse_args()


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def plot_class_balance(df: pd.DataFrame, out: Path) -> None:
    counts = df[TARGET_COLUMN].astype(bool).value_counts().reindex([False, True], fill_value=0)
    plt.figure(figsize=(5, 4))
    plt.bar(["no surrender", "surrender"], counts.values, color=["#4c78a8", "#f58518"])
    plt.ylabel("team rows")
    plt.title("Surrender class balance")
    for i, value in enumerate(counts.values):
        plt.text(i, value, str(int(value)), ha="center", va="bottom")
    savefig(out / "01_class_balance.png")


def plot_duration(df: pd.DataFrame, out: Path) -> None:
    plt.figure(figsize=(6, 4))
    plt.hist(df["game_duration_sec"] / 60, bins=min(20, max(5, df["game_duration_sec"].nunique())), color="#72b7b2")
    plt.xlabel("game duration (minutes)")
    plt.ylabel("team rows")
    plt.title("Game duration distribution")
    savefig(out / "02_game_duration_distribution.png")


def plot_surrender_rate_by_binned_feature(df: pd.DataFrame, feature: str, out: Path, filename: str) -> None:
    series = df[feature]
    if series.nunique() <= 1:
        grouped = df.assign(bin=series.astype(str)).groupby("bin")[TARGET_COLUMN].mean()
    else:
        bins = min(6, series.nunique())
        try:
            labels = pd.qcut(series, q=bins, duplicates="drop")
        except ValueError:
            labels = pd.cut(series, bins=bins, duplicates="drop")
        grouped = df.assign(bin=labels.astype(str)).groupby("bin", sort=False)[TARGET_COLUMN].mean()
    plt.figure(figsize=(8, 4))
    plt.bar(range(len(grouped)), grouped.values, color="#e45756")
    plt.xticks(range(len(grouped)), grouped.index.astype(str), rotation=30, ha="right")
    plt.ylabel("surrender rate")
    plt.ylim(0, min(1.0, max(0.05, float(grouped.max()) * 1.25 if len(grouped) else 1)))
    plt.title(f"Surrender rate by {feature}")
    savefig(out / filename)


def plot_objective_summary(df: pd.DataFrame, out: Path) -> None:
    objective_cols = ["tower_diff_15", "dragon_diff_15", "rift_herald_diff_15"]
    means = df.groupby(df[TARGET_COLUMN].astype(bool))[objective_cols].mean().reindex([False, True]).fillna(0)
    x = np.arange(len(objective_cols))
    width = 0.35
    plt.figure(figsize=(7, 4))
    plt.bar(x - width / 2, means.loc[False].values, width, label="no surrender")
    plt.bar(x + width / 2, means.loc[True].values, width, label="surrender")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xticks(x, objective_cols, rotation=20, ha="right")
    plt.ylabel("mean team-perspective diff")
    plt.title("Objective differences by label")
    plt.legend()
    savefig(out / "05_objective_differences_by_label.png")


def plot_correlation(df: pd.DataFrame, out: Path) -> None:
    corr = df[FEATURE_COLUMNS].corr(numeric_only=True).fillna(0)
    plt.figure(figsize=(8, 7))
    im = plt.imshow(corr.values, vmin=-1, vmax=1, cmap="coolwarm")
    plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=90)
    plt.yticks(range(len(corr.index)), corr.index)
    plt.title("Feature correlation heatmap")
    savefig(out / "06_feature_correlation_heatmap.png")


def plot_model_metrics(metrics_csv: Path, out: Path) -> bool:
    if not metrics_csv.exists():
        return False
    metrics = pd.read_csv(metrics_csv)
    test = metrics[metrics["split"] == "test"].copy()
    if test.empty:
        return False
    metric_cols = ["f1", "roc_auc", "pr_auc"]
    x = np.arange(len(test))
    width = 0.25
    plt.figure(figsize=(8, 4))
    for offset, metric in enumerate(metric_cols):
        values = pd.to_numeric(test[metric], errors="coerce").fillna(0).values
        plt.bar(x + (offset - 1) * width, values, width, label=metric)
    plt.xticks(x, test["model"], rotation=25, ha="right")
    plt.ylim(0, 1)
    plt.ylabel("score")
    plt.title("Test metric comparison")
    plt.legend()
    savefig(out / "07_model_metric_comparison.png")
    return True


def main() -> int:
    args = parse_args()
    settings = load_settings()
    input_path = args.input or (settings.processed_data_dir / "team_features.csv")
    figure_dir = args.figure_dir or settings.figure_dir
    metrics_csv = args.metrics_csv or (settings.output_dir / "tables" / "model_comparison.csv")
    df = pd.read_csv(input_path)
    if df.empty:
        raise SystemExit("Input dataset is empty")

    plot_class_balance(df, figure_dir)
    plot_duration(df, figure_dir)
    plot_surrender_rate_by_binned_feature(df, "gold_diff_15", figure_dir, "03_surrender_rate_by_gold_diff.png")
    plot_surrender_rate_by_binned_feature(df, "kill_diff_15", figure_dir, "04_surrender_rate_by_kill_diff.png")
    plot_objective_summary(df, figure_dir)
    plot_correlation(df, figure_dir)
    has_model_metrics = plot_model_metrics(metrics_csv, figure_dir)

    manifest = {
        "created_at": utc_now_iso(),
        "input_csv": str(input_path),
        "figure_dir": str(figure_dir),
        "row_count": int(len(df)),
        "positive_rows": int(df[TARGET_COLUMN].astype(bool).sum()),
        "generated_figures": sorted(str(p) for p in figure_dir.glob("*.png")),
        "model_metrics_figure_generated": has_model_metrics,
    }
    atomic_write_json(figure_dir / "eda_manifest.json", manifest)
    print("eda_complete")
    print(f"figure_dir: {figure_dir}")
    print(f"figures: {len(manifest['generated_figures'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
