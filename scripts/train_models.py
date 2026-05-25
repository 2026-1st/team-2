#!/usr/bin/env python3
"""Train baseline ML models on the processed team-feature dataset."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import joblib  # noqa: E402
import pandas as pd  # noqa: E402

from team2_surrender.config import load_settings  # noqa: E402
from team2_surrender.modeling import GROUP_COLUMN, TARGET_COLUMN, train_models  # noqa: E402
from team2_surrender.storage import atomic_write_json  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--metrics-json", type=Path, default=None)
    parser.add_argument("--metrics-csv", type=Path, default=None)
    parser.add_argument("--model-dir", type=Path, default=None)
    parser.add_argument("--group-col", default=GROUP_COLUMN)
    parser.add_argument("--target", default=TARGET_COLUMN)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def write_metrics_csv(path: Path, results: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for model_name, model_result in results["models"].items():
        for split_name in ("valid", "test"):
            metrics = model_result[split_name]
            rows.append({
                "model": model_name,
                "split": split_name,
                "accuracy": metrics["accuracy"],
                "f1": metrics["f1"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "roc_auc": metrics["roc_auc"],
                "pr_auc": metrics["pr_auc"],
                "confusion_matrix": json.dumps(metrics["confusion_matrix"]),
            })
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    settings = load_settings()
    input_path = args.input or (settings.processed_data_dir / "team_features.csv")
    metrics_json = args.metrics_json or (settings.output_dir / "metrics" / "model_comparison.json")
    metrics_csv = args.metrics_csv or (settings.output_dir / "tables" / "model_comparison.csv")
    model_dir = args.model_dir or settings.model_dir

    df = pd.read_csv(input_path)
    models, results = train_models(df, group_col=args.group_col, target_col=args.target, random_state=args.random_state)

    atomic_write_json(metrics_json, results)
    write_metrics_csv(metrics_csv, results)
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, model in models.items():
        joblib.dump(model, model_dir / f"{name}.joblib")

    print("model_training_complete")
    print(f"input: {input_path}")
    print(f"metrics_json: {metrics_json}")
    print(f"metrics_csv: {metrics_csv}")
    print(f"model_dir: {model_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
