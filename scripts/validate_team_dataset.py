#!/usr/bin/env python3
"""Validate the processed team-feature dataset against project acceptance gates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from team2_surrender.config import load_settings  # noqa: E402
from team2_surrender.dataset import PUBLIC_FORBIDDEN_COLUMNS, TEAM_FEATURE_COLUMNS  # noqa: E402
from team2_surrender.modeling import FEATURE_COLUMNS, GROUP_COLUMN, TARGET_COLUMN  # noqa: E402
from team2_surrender.storage import atomic_write_json, utc_now_iso  # noqa: E402


POTENTIAL_IDENTIFIER_SUBSTRINGS = [
    "puuid",
    "summoner",
    "riotid",
    "riot_id",
    "accountid",
    "account_id",
    "api_key",
    "service_role",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--min-rows", type=int, default=1000)
    parser.add_argument("--min-features", type=int, default=10)
    parser.add_argument("--min-groups", type=int, default=3)
    parser.add_argument("--allow-small", action="store_true", help="Relax row threshold for fixture/smoke datasets")
    parser.add_argument("--allow-single-class", action="store_true", help="Allow one-class labels for collection smoke datasets; not valid for final modeling")
    return parser.parse_args()


def fail(checks: list[dict[str, Any]], name: str, message: str, evidence: Any = None) -> None:
    checks.append({"name": name, "ok": False, "message": message, "evidence": evidence})


def ok(checks: list[dict[str, Any]], name: str, message: str, evidence: Any = None) -> None:
    checks.append({"name": name, "ok": True, "message": message, "evidence": evidence})


def validate(
    df: pd.DataFrame,
    min_rows: int,
    min_features: int,
    min_groups: int,
    allow_small: bool,
    allow_single_class: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    missing_required = [col for col in TEAM_FEATURE_COLUMNS if col not in df.columns]
    if missing_required:
        fail(checks, "required_columns", "Missing required columns", missing_required)
    else:
        ok(checks, "required_columns", "All required columns are present", TEAM_FEATURE_COLUMNS)

    row_count = len(df)
    if row_count >= min_rows or allow_small:
        ok(checks, "row_count", f"Row count is {'small but allowed' if allow_small and row_count < min_rows else 'sufficient'}", row_count)
    else:
        fail(checks, "row_count", f"Need at least {min_rows} team rows", row_count)

    present_features = [col for col in FEATURE_COLUMNS if col in df.columns]
    if len(present_features) >= min_features:
        ok(checks, "feature_count", f"At least {min_features} feature columns present", present_features)
    else:
        fail(checks, "feature_count", f"Need at least {min_features} feature columns", present_features)

    forbidden_exact = sorted(set(df.columns) & PUBLIC_FORBIDDEN_COLUMNS)
    forbidden_fuzzy = sorted([
        col for col in df.columns
        if any(token in col.lower() for token in POTENTIAL_IDENTIFIER_SUBSTRINGS)
    ])
    forbidden = sorted(set(forbidden_exact + forbidden_fuzzy))
    if forbidden:
        fail(checks, "privacy_columns", "Forbidden or suspicious identifier/key columns found", forbidden)
    else:
        ok(checks, "privacy_columns", "No forbidden identifier/key columns found")

    if TARGET_COLUMN in df.columns:
        target_values = df[TARGET_COLUMN].astype(str).str.lower().unique().tolist()
        positive_count = int(df[TARGET_COLUMN].astype(str).str.lower().isin(["true", "1", "t", "yes"]).sum())
        class_count = len(set(target_values))
        if class_count >= 2:
            ok(checks, "target_classes", "Target contains at least two classes", {"values": target_values, "positive_count": positive_count})
        elif allow_single_class:
            checks.append({
                "name": "target_classes",
                "ok": True,
                "severity": "warning",
                "message": "Target has one class; allowed for collection smoke only, not final modeling",
                "evidence": {"values": target_values, "positive_count": positive_count},
            })
        else:
            fail(checks, "target_classes", "Target must contain at least two classes for modeling", {"values": target_values, "positive_count": positive_count})
    else:
        fail(checks, "target_classes", f"Missing target column {TARGET_COLUMN}")

    if GROUP_COLUMN in df.columns:
        group_count = int(df[GROUP_COLUMN].nunique())
        if group_count >= min_groups:
            ok(checks, "group_count", f"At least {min_groups} unique match groups present", group_count)
        else:
            fail(checks, "group_count", f"Need at least {min_groups} unique match groups", group_count)

        group_sizes = df.groupby(GROUP_COLUMN).size()
        unusual = group_sizes[group_sizes != 2]
        if unusual.empty:
            ok(checks, "two_rows_per_match", "Every match has exactly two team rows")
        else:
            severity = "warning" if allow_small else "error"
            checks.append({
                "name": "two_rows_per_match",
                "ok": allow_small,
                "severity": severity,
                "message": "Some matches do not have exactly two team rows",
                "evidence": unusual.head(20).to_dict(),
            })
    else:
        fail(checks, "group_count", f"Missing group column {GROUP_COLUMN}")
        fail(checks, "two_rows_per_match", f"Missing group column {GROUP_COLUMN}")

    if GROUP_COLUMN in df.columns and TARGET_COLUMN in df.columns:
        bool_target = df[TARGET_COLUMN].astype(str).str.lower().isin(["true", "1", "t", "yes"])
        positives_per_match = bool_target.groupby(df[GROUP_COLUMN]).sum()
        impossible = positives_per_match[positives_per_match > 1]
        if impossible.empty:
            ok(checks, "positive_labels_per_match", "No match has more than one surrender-defeat team")
        else:
            fail(
                checks,
                "positive_labels_per_match",
                "A match cannot have more than one surrender-defeat team",
                impossible.head(20).astype(int).to_dict(),
            )

    if "queue_id" in df.columns:
        bad_queue = sorted(set(pd.to_numeric(df["queue_id"], errors="coerce").dropna().astype(int)) - {420})
        if bad_queue:
            fail(checks, "queue_id", "Non-ranked-solo queue ids found", bad_queue)
        else:
            ok(checks, "queue_id", "All rows use queue_id=420")

    if "game_duration_sec" in df.columns:
        durations = pd.to_numeric(df["game_duration_sec"], errors="coerce")
        too_short = int((durations < 900).sum())
        missing = int(durations.isna().sum())
        if too_short or missing:
            fail(checks, "duration", "Invalid or under-15-minute rows found", {"under_900": too_short, "missing": missing})
        else:
            ok(checks, "duration", "All rows have game_duration_sec >= 900")

    failed = [check for check in checks if not check.get("ok")]
    status = "failed" if failed else "complete"
    return status, checks


def main() -> int:
    args = parse_args()
    settings = load_settings()
    input_path = args.input or (settings.processed_data_dir / "team_features.csv")
    report_path = args.report or (settings.processed_data_dir / "team_features_validation.json")
    if not input_path.exists():
        raise SystemExit(f"Input CSV not found: {input_path}")
    df = pd.read_csv(input_path)
    status, checks = validate(df, args.min_rows, args.min_features, args.min_groups, args.allow_small, args.allow_single_class)
    report = {
        "created_at": utc_now_iso(),
        "input_csv": str(input_path),
        "status": status,
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "checks": checks,
    }
    atomic_write_json(report_path, report)
    print(f"dataset_validation_status: {status}")
    print(f"input_csv: {input_path}")
    print(f"report: {report_path}")
    for check in checks:
        print(f" - [{'OK' if check.get('ok') else 'FAIL'}] {check['name']}: {check['message']}")
    return 0 if status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
