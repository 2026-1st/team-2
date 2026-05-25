#!/usr/bin/env python3
"""Upload processed team feature CSV rows to Supabase via the Data API.

The script upserts parent ``riot_matches`` rows first, then ``team_features``.
It defaults to dry-run mode; pass ``--execute`` to write to Supabase.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team2_surrender.config import load_settings  # noqa: E402

TEAM_FEATURE_COLUMNS = {
    "match_id",
    "team_id",
    "feature_version",
    "team_surrendered",
    "queue_id",
    "game_version",
    "game_duration_sec",
    "collected_at",
    "gold_diff_15",
    "kill_diff_15",
    "tower_diff_15",
    "dragon_diff_15",
    "rift_herald_diff_15",
    "cs_diff_15",
    "avg_level_diff_15",
    "first_blood",
    "first_tower",
    "ward_placed_diff_15",
    "ward_kill_diff_15",
}

INT_COLUMNS = {
    "team_id",
    "queue_id",
    "game_duration_sec",
    "gold_diff_15",
    "kill_diff_15",
    "tower_diff_15",
    "dragon_diff_15",
    "rift_herald_diff_15",
    "cs_diff_15",
    "first_blood",
    "first_tower",
    "ward_placed_diff_15",
    "ward_kill_diff_15",
}
FLOAT_COLUMNS = {"avg_level_diff_15"}
BOOL_COLUMNS = {"team_surrendered"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/riot/team_features.csv"))
    parser.add_argument("--execute", action="store_true", help="Actually write rows to Supabase. Default is dry-run.")
    parser.add_argument("--batch-size", type=int, default=500)
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def convert_row(row: dict[str, str]) -> dict[str, Any]:
    converted: dict[str, Any] = {}
    for key in TEAM_FEATURE_COLUMNS:
        value = row.get(key)
        if value in (None, ""):
            converted[key] = None
        elif key in INT_COLUMNS:
            converted[key] = int(value)
        elif key in FLOAT_COLUMNS:
            converted[key] = float(value)
        elif key in BOOL_COLUMNS:
            converted[key] = parse_bool(value)
        else:
            converted[key] = value
    return converted


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Input CSV not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = sorted(TEAM_FEATURE_COLUMNS - set(reader.fieldnames or []))
        if missing:
            raise SystemExit("Input CSV is missing required columns: " + ", ".join(missing))
        return [convert_row(row) for row in reader]


def build_riot_match_rows(team_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_match: dict[str, dict[str, Any]] = {}
    for row in team_rows:
        match_id = row["match_id"]
        if match_id not in by_match:
            by_match[match_id] = {
                "match_id": match_id,
                "queue_id": row["queue_id"],
                "game_version": row.get("game_version"),
                "game_duration_sec": row["game_duration_sec"],
                "collected_at": row.get("collected_at"),
                "has_detail": True,
                "has_timeline": True,
                "excluded": False,
            }
    return list(by_match.values())


def supabase_base_url() -> tuple[str, str]:
    load_settings()  # loads .env into os.environ
    url = __import__("os").getenv("SUPABASE_URL", "").rstrip("/")
    key = __import__("os").getenv("SUPABASE_SERVICE_ROLE_KEY") or __import__("os").getenv("SUPABASE_ANON_KEY", "")
    if not url or "your-" in url or "your_" in url:
        raise SystemExit("SUPABASE_URL is missing in .env")
    if not key or "your_" in key:
        raise SystemExit("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY is missing in .env")
    return url, key


def post_upsert(table: str, rows: list[dict[str, Any]], on_conflict: str, batch_size: int) -> None:
    if not rows:
        return
    base_url, key = supabase_base_url()
    endpoint = f"{base_url}/rest/v1/{table}?" + urllib.parse.urlencode({"on_conflict": on_conflict}, safe=",")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        request = urllib.request.Request(endpoint, data=json.dumps(batch).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
            raise SystemExit(f"Supabase upload failed table={table} status={exc.code}: {body}") from exc


def main() -> int:
    args = parse_args()
    team_rows = load_rows(args.input)
    match_rows = build_riot_match_rows(team_rows)
    print(f"input_csv: {args.input}")
    print(f"riot_matches_to_upsert: {len(match_rows)}")
    print(f"team_features_to_upsert: {len(team_rows)}")
    if not args.execute:
        print("dry_run_complete: pass --execute to write to Supabase")
        return 0
    post_upsert("riot_matches", match_rows, "match_id", args.batch_size)
    post_upsert("team_features", team_rows, "match_id,team_id,feature_version", args.batch_size)
    print("supabase_upload_complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
