#!/usr/bin/env python3
"""Prepare local artifacts required by the Riot surrender analysis notebook.

This script keeps the notebook reproducible without reading directly from
Supabase. It uses the processed CSV as the analysis boundary and regenerates
validation, model, metric, figure, and local upload-verification artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ID = "riot-scale-2600"
REPORT_PATH = ROOT / "outputs" / "verification" / "jupyter_analysis_artifacts.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID, help="Run id used in generated artifact names")
    parser.add_argument("--raw-run-id", default=None, help="Raw Riot run id. Defaults to --run-id")
    parser.add_argument("--rebuild-dataset", action="store_true", help="Rebuild processed CSV from data/raw/riot/runs/<raw-run-id>")
    parser.add_argument("--report", type=Path, default=REPORT_PATH, help="Preparation report path")
    parser.add_argument("--execute-notebook", action="store_true", help="Execute the main notebook after artifacts are ready")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", "src")
    env.setdefault("PYTHONPYCACHEPREFIX", "/tmp/team2-pycache")
    env.setdefault("MPLBACKEND", "Agg")
    env.setdefault("MPLCONFIGDIR", "/tmp/team2-matplotlib")
    env.setdefault("XDG_CACHE_HOME", "/tmp/team2-cache")
    env.setdefault("LOKY_MAX_CPU_COUNT", "2")
    Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
    return env


def run_step(name: str, command: list[str], report: dict[str, Any]) -> None:
    print(f"\n[prepare] {name}")
    print("$", " ".join(command))
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=command_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout or ""
    print(output[-4000:], end="" if output.endswith("\n") else "\n")
    report["steps"].append({
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "output_tail": output[-4000:],
    })
    if result.returncode != 0:
        write_report(report)
        raise SystemExit(result.returncode)


def count_team_rows(csv_path: Path) -> dict[str, int]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    match_ids = {row["match_id"] for row in rows}
    positive_rows = sum(1 for row in rows if str(row.get("team_surrendered", "")).lower() in {"1", "true", "t", "yes"})
    return {
        "matches": len(match_ids),
        "team_rows": len(rows),
        "positive_rows": positive_rows,
    }


def write_local_upload_verification(csv_path: Path, verification_path: Path) -> dict[str, Any]:
    counts = count_team_rows(csv_path)
    verification = {
        "status": "complete",
        "mode": "local_csv_dry_run",
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_csv": rel(csv_path),
        "expected_matches": counts["matches"],
        "expected_team_rows": counts["team_rows"],
        "expected_positive_rows": counts["positive_rows"],
        "actual_matches": counts["matches"],
        "actual_team_rows": counts["team_rows"],
        "actual_positive_rows": counts["positive_rows"],
        "note": "Generated from local CSV for notebook reproducibility; no Supabase network write was performed.",
    }
    verification_path.parent.mkdir(parents=True, exist_ok=True)
    verification_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"upload_verification: {rel(verification_path)}")
    return verification


def assert_required(paths: dict[str, Path]) -> None:
    missing = [f"{name}: {rel(path)}" for name, path in paths.items() if not path.exists()]
    if missing:
        message = "Missing required Jupyter analysis artifacts:\n" + "\n".join(missing)
        raise SystemExit(message)


def write_report(report: dict[str, Any]) -> None:
    path = Path(report["report_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_id = args.run_id
    raw_run_id = args.raw_run_id or run_id

    csv_path = ROOT / "data" / "processed" / "riot" / f"{run_id}_team_features.csv"
    manifest_path = ROOT / "data" / "processed" / "riot" / f"{run_id}_team_features_manifest.json"
    validation_path = ROOT / "data" / "processed" / "riot" / f"{run_id}_team_features_validation_strict.json"
    metrics_json = ROOT / "outputs" / "metrics" / f"{run_id}_model_comparison.json"
    metrics_csv = ROOT / "outputs" / "tables" / f"{run_id}_model_comparison.csv"
    model_dir = ROOT / "models" / run_id
    figure_dir = ROOT / "reports" / "figures" / run_id
    upload_verification = ROOT / "outputs" / "verification" / f"supabase_upload_{run_id}.json"
    notebook_path = ROOT / "notebooks" / "team2_riot_surrender_analysis.ipynb"

    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report_path": str(args.report),
        "run_id": run_id,
        "raw_run_id": raw_run_id,
        "status": "running",
        "steps": [],
        "artifacts": {},
    }

    raw_run_dir = ROOT / "data" / "raw" / "riot" / "runs" / raw_run_id
    if args.rebuild_dataset or not csv_path.exists():
        if not raw_run_dir.exists():
            raise SystemExit(
                "Processed CSV is missing and raw run is unavailable.\n"
                f"Expected raw run: {rel(raw_run_dir)}\n"
                "Create the raw run with scripts/collect_riot_matches.py first, "
                "or place the processed CSV at "
                f"{rel(csv_path)}."
            )
        run_step(
            "build_dataset",
            [
                sys.executable,
                "scripts/build_team_dataset.py",
                "--run-id",
                raw_run_id,
                "--out",
                str(csv_path),
                "--manifest",
                str(manifest_path),
            ],
            report,
        )
    else:
        print(f"[prepare] build_dataset skipped: {rel(csv_path)} already exists")

    run_step(
        "validate_dataset_strict",
        [
            sys.executable,
            "scripts/validate_team_dataset.py",
            "--input",
            str(csv_path),
            "--report",
            str(validation_path),
        ],
        report,
    )
    run_step(
        "train_models",
        [
            sys.executable,
            "scripts/train_models.py",
            "--input",
            str(csv_path),
            "--metrics-json",
            str(metrics_json),
            "--metrics-csv",
            str(metrics_csv),
            "--model-dir",
            str(model_dir),
        ],
        report,
    )
    run_step(
        "run_eda",
        [
            sys.executable,
            "scripts/run_eda.py",
            "--input",
            str(csv_path),
            "--figure-dir",
            str(figure_dir),
            "--metrics-csv",
            str(metrics_csv),
        ],
        report,
    )

    verification = write_local_upload_verification(csv_path, upload_verification)
    report["steps"].append({
        "name": "write_local_upload_verification",
        "command": [],
        "returncode": 0,
        "ok": True,
        "output_tail": json.dumps(verification, ensure_ascii=False),
    })

    required = {
        "team_features_csv": csv_path,
        "validation_strict_json": validation_path,
        "metrics_json": metrics_json,
        "metrics_csv": metrics_csv,
        "model_dir": model_dir,
        "logistic_model": model_dir / "logistic_regression.joblib",
        "random_forest_model": model_dir / "random_forest.joblib",
        "figure_dir": figure_dir,
        "upload_verification": upload_verification,
    }
    assert_required(required)

    if args.execute_notebook:
        run_step(
            "execute_main_notebook",
            [
                sys.executable,
                "-m",
                "jupyter",
                "nbconvert",
                "--to",
                "notebook",
                "--execute",
                str(notebook_path),
                "--output",
                str(ROOT / "notebooks" / "team2_riot_surrender_analysis.executed.ipynb"),
                "--ExecutePreprocessor.timeout=300",
            ],
            report,
        )

    for name, path in required.items():
        report["artifacts"][name] = {"path": rel(path), "exists": path.exists()}
    report["status"] = "complete"
    write_report(report)
    print(f"\npreparation_status: {report['status']}")
    print(f"report: {rel(Path(args.report))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
