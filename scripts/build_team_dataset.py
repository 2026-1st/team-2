#!/usr/bin/env python3
"""Build the processed team-feature CSV from collected Riot raw JSON."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team2_surrender.config import load_settings
from team2_surrender.dataset import TEAM_FEATURE_COLUMNS
from team2_surrender.features import match_to_team_rows
from team2_surrender.storage import atomic_write_json, read_json, utc_now_iso


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=None, help="Base raw Riot dir, default from .env")
    parser.add_argument("--run-id", default=None, help="Specific run id under raw-dir/runs")
    parser.add_argument("--out", type=Path, default=None, help="Output CSV path")
    parser.add_argument("--manifest", type=Path, default=None, help="Output build manifest path")
    return parser.parse_args()


def run_paths(raw_dir: Path, run_id: str | None) -> list[Path]:
    runs_root = raw_dir / "runs"
    if run_id:
        path = runs_root / run_id
        return [path]
    if not runs_root.exists():
        return []
    return sorted([p for p in runs_root.iterdir() if p.is_dir()])


def match_ids_for_run(path: Path) -> list[str]:
    manifest_path = path / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        ids = manifest.get("match_ids", [])
        if isinstance(ids, list):
            return [str(x) for x in ids]
    return sorted(p.stem for p in (path / "matches").glob("*.json"))


def load_match_pair(run_path: Path, match_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    detail_path = run_path / "matches" / f"{match_id}.json"
    timeline_path = run_path / "timelines" / f"{match_id}.json"
    if not detail_path.exists() or not timeline_path.exists():
        return None
    return read_json(detail_path), read_json(timeline_path)


def main() -> int:
    args = parse_args()
    settings = load_settings()
    raw_dir = args.raw_dir or settings.raw_data_dir
    out = args.out or (settings.processed_data_dir / "team_features.csv")
    manifest_path = args.manifest or (settings.processed_data_dir / "team_features_manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    counts = Counter()
    exclusions = Counter()
    processed_at = utc_now_iso()
    source_runs: list[str] = []

    for run_path in run_paths(raw_dir, args.run_id):
        if not run_path.exists():
            continue
        source_runs.append(str(run_path))
        for match_id in match_ids_for_run(run_path):
            pair = load_match_pair(run_path, match_id)
            if pair is None:
                counts["missing_pair"] += 1
                continue
            detail, timeline = pair
            team_rows, reason = match_to_team_rows(detail, timeline, required_queue_id=settings.riot_queue_id)
            if reason:
                exclusions[reason] += 1
                continue
            for row in team_rows:
                row["collected_at"] = processed_at
                rows.append(row)
            counts["eligible_matches"] += 1

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEAM_FEATURE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    label_positive = sum(1 for row in rows if bool(row.get("team_surrendered")))
    manifest = {
        "created_at": processed_at,
        "source_runs": source_runs,
        "output_csv": str(out),
        "team_rows": len(rows),
        "eligible_matches": counts["eligible_matches"],
        "positive_team_surrendered_rows": label_positive,
        "positive_rate": round(label_positive / len(rows), 6) if rows else 0,
        "exclusions": dict(exclusions),
        "counts": dict(counts),
        "columns": TEAM_FEATURE_COLUMNS,
    }
    atomic_write_json(manifest_path, manifest)
    print("dataset_build_complete")
    print(f"output_csv: {out}")
    print(f"team_rows: {len(rows)}")
    print(f"eligible_matches: {counts['eligible_matches']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
