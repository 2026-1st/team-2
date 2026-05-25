#!/usr/bin/env python3
"""Run the local no-network verification pipeline for the Team 2 project.

This verifier intentionally avoids Riot/Supabase network writes. It proves that
code compiles, unit tests pass, collector dry-run works, fixture raw data can be
converted to processed team features, processed rows can be counted for Supabase
upload dry-run, and fixture-scale model/EDA outputs can be generated.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "outputs" / "verification" / "local_pipeline_verification.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--keep-going", action="store_true", help="Run all checks even after one fails")
    return parser.parse_args()


def env() -> dict[str, str]:
    out = os.environ.copy()
    out.setdefault("PYTHONPATH", "src")
    out.setdefault("PYTHONPYCACHEPREFIX", "/tmp/team2-pycache")
    out.setdefault("MPLBACKEND", "Agg")
    out.setdefault("MPLCONFIGDIR", "/tmp/team2-matplotlib")
    out.setdefault("XDG_CACHE_HOME", "/tmp/team2-cache")
    out.setdefault("LOKY_MAX_CPU_COUNT", "2")
    Path(out["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(out["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
    return out


def run_step(name: str, command: list[str], keep_going: bool, report: dict[str, Any]) -> bool:
    print(f"\n[verify] {name}")
    print("$", " ".join(command))
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout or ""
    print(output[-4000:], end="" if output.endswith("\n") else "\n")
    ok = result.returncode == 0
    report["steps"].append({
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "ok": ok,
        "output_tail": output[-4000:],
    })
    if not ok and not keep_going:
        report["status"] = "failed"
        write_report(report)
        raise SystemExit(result.returncode)
    return ok


def write_report(report: dict[str, Any]) -> None:
    path = Path(report["report_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report_path": str(args.report),
        "status": "running",
        "steps": [],
        "artifacts": {},
    }

    checks = [
        ("compile", [sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"]),
        ("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        (
            "collector_dry_run",
            [
                sys.executable,
                "scripts/collect_riot_matches.py",
                "--dry-run",
                "--run-id",
                "verify-local-dryrun",
                "--max-seeds",
                "1",
                "--max-unique-matches",
                "1",
            ],
        ),
        ("create_fixture_raw_run", [sys.executable, "tests/create_fixture_raw_run.py"]),
        (
            "build_fixture_dataset",
            [
                sys.executable,
                "scripts/build_team_dataset.py",
                "--run-id",
                "fixture-e2e",
                "--out",
                "data/processed/riot/fixture_team_features.csv",
                "--manifest",
                "data/processed/riot/fixture_team_features_manifest.json",
            ],
        ),
        (
            "supabase_rest_upload_dry_run",
            [
                sys.executable,
                "scripts/upload_team_features_supabase.py",
                "--input",
                "data/processed/riot/fixture_team_features.csv",
            ],
        ),
        (
            "supabase_postgres_upload_dry_run",
            [
                sys.executable,
                "scripts/upload_team_features_postgres.py",
                "--input",
                "data/processed/riot/fixture_team_features.csv",
            ],
        ),
        ("create_fixture_model_dataset", [sys.executable, "tests/create_fixture_model_dataset.py"]),
        (
            "validate_fixture_model_dataset",
            [
                sys.executable,
                "scripts/validate_team_dataset.py",
                "--input",
                "data/processed/riot/fixture_model_team_features.csv",
                "--report",
                "data/processed/riot/fixture_model_validation.json",
                "--allow-small",
            ],
        ),
        (
            "train_fixture_models",
            [
                sys.executable,
                "scripts/train_models.py",
                "--input",
                "data/processed/riot/fixture_model_team_features.csv",
                "--metrics-json",
                "outputs/metrics/fixture_model_comparison.json",
                "--metrics-csv",
                "outputs/tables/fixture_model_comparison.csv",
                "--model-dir",
                "models/fixture",
            ],
        ),
        (
            "fixture_eda",
            [
                sys.executable,
                "scripts/run_eda.py",
                "--input",
                "data/processed/riot/fixture_model_team_features.csv",
                "--figure-dir",
                "reports/figures/fixture",
                "--metrics-csv",
                "outputs/tables/fixture_model_comparison.csv",
            ],
        ),
    ]

    all_ok = True
    for name, command in checks:
        all_ok = run_step(name, command, args.keep_going, report) and all_ok

    artifacts = {
        "fixture_team_features_csv": ROOT / "data/processed/riot/fixture_team_features.csv",
        "fixture_team_features_manifest": ROOT / "data/processed/riot/fixture_team_features_manifest.json",
        "fixture_model_validation": ROOT / "data/processed/riot/fixture_model_validation.json",
        "fixture_model_metrics_json": ROOT / "outputs/metrics/fixture_model_comparison.json",
        "fixture_model_metrics_csv": ROOT / "outputs/tables/fixture_model_comparison.csv",
        "fixture_eda_manifest": ROOT / "reports/figures/fixture/eda_manifest.json",
    }
    for key, path in artifacts.items():
        report["artifacts"][key] = {"path": str(path.relative_to(ROOT)), "exists": path.exists()}

    report["status"] = "complete" if all_ok and all(v["exists"] for v in report["artifacts"].values()) else "failed"
    write_report(report)
    print(f"\nverification_status: {report['status']}")
    print(f"report: {args.report}")
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
