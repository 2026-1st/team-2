#!/usr/bin/env python3
"""Upload processed team feature CSV rows via direct Supabase/Postgres upsert.

This path does not depend on PostgREST/Data API table exposure settings, so it is
useful when "Automatically expose new tables" is disabled in Supabase.
Defaults to dry-run; pass --execute to write rows.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: psycopg2. Install psycopg2-binary.") from exc

from team2_surrender.config import load_settings  # noqa: E402
from team2_surrender.db import require_conn_kwargs  # noqa: E402

TEAM_FEATURE_COLUMNS = [
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
]
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
    parser.add_argument("--execute", action="store_true", help="Actually write rows to Supabase/Postgres")
    parser.add_argument("--batch-size", type=int, default=500)
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def convert_row(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in TEAM_FEATURE_COLUMNS:
        value = row.get(key)
        if value in (None, ""):
            out[key] = None
        elif key in INT_COLUMNS:
            out[key] = int(value)
        elif key in FLOAT_COLUMNS:
            out[key] = float(value)
        elif key in BOOL_COLUMNS:
            out[key] = parse_bool(value)
        else:
            out[key] = value
    return out


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Input CSV not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [col for col in TEAM_FEATURE_COLUMNS if col not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit("Input CSV missing required columns: " + ", ".join(missing))
        return [convert_row(row) for row in reader]


def build_match_rows(team_rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    by_match: dict[str, tuple[Any, ...]] = {}
    for row in team_rows:
        match_id = row["match_id"]
        by_match.setdefault(
            match_id,
            (
                match_id,
                row["queue_id"],
                row.get("game_version"),
                row["game_duration_sec"],
                row.get("collected_at"),
                True,
                True,
                False,
            ),
        )
    return list(by_match.values())


def build_feature_tuples(team_rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [tuple(row.get(col) for col in TEAM_FEATURE_COLUMNS) for row in team_rows]


def upsert_postgres(team_rows: list[dict[str, Any]], batch_size: int) -> None:
    conn_kwargs = require_conn_kwargs()
    match_rows = build_match_rows(team_rows)
    feature_rows = build_feature_tuples(team_rows)
    match_sql = """
        insert into public.riot_matches (
          match_id, queue_id, game_version, game_duration_sec, collected_at,
          has_detail, has_timeline, excluded
        ) values %s
        on conflict (match_id) do update set
          queue_id = excluded.queue_id,
          game_version = excluded.game_version,
          game_duration_sec = excluded.game_duration_sec,
          collected_at = excluded.collected_at,
          has_detail = excluded.has_detail,
          has_timeline = excluded.has_timeline,
          excluded = excluded.excluded,
          updated_at = now()
    """
    feature_sql = f"""
        insert into public.team_features ({", ".join(TEAM_FEATURE_COLUMNS)}) values %s
        on conflict (match_id, team_id, feature_version) do update set
          team_surrendered = excluded.team_surrendered,
          queue_id = excluded.queue_id,
          game_version = excluded.game_version,
          game_duration_sec = excluded.game_duration_sec,
          collected_at = excluded.collected_at,
          gold_diff_15 = excluded.gold_diff_15,
          kill_diff_15 = excluded.kill_diff_15,
          tower_diff_15 = excluded.tower_diff_15,
          dragon_diff_15 = excluded.dragon_diff_15,
          rift_herald_diff_15 = excluded.rift_herald_diff_15,
          cs_diff_15 = excluded.cs_diff_15,
          avg_level_diff_15 = excluded.avg_level_diff_15,
          first_blood = excluded.first_blood,
          first_tower = excluded.first_tower,
          ward_placed_diff_15 = excluded.ward_placed_diff_15,
          ward_kill_diff_15 = excluded.ward_kill_diff_15,
          updated_at = now()
    """
    print("connection_info: set (value hidden)")
    print(f"db_host: {conn_kwargs['host']}")
    with psycopg2.connect(**conn_kwargs) as conn:
        with conn.cursor() as cur:
            execute_values(cur, match_sql, match_rows, page_size=batch_size)
            execute_values(cur, feature_sql, feature_rows, page_size=batch_size)
        conn.commit()


def main() -> int:
    args = parse_args()
    load_settings()  # load .env
    rows = load_rows(args.input)
    print(f"input_csv: {args.input}")
    print(f"riot_matches_to_upsert: {len(build_match_rows(rows))}")
    print(f"team_features_to_upsert: {len(rows)}")
    if not args.execute:
        print("dry_run_complete: pass --execute to write via Postgres")
        return 0
    upsert_postgres(rows, args.batch_size)
    print("postgres_upload_complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
