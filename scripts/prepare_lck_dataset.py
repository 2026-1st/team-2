#!/usr/bin/env python3
"""Fetch and prepare a minimal LCK early-game dataset from Oracle's Elixir CSVs.

This script streams public yearly CSV files from a Hugging Face mirror of
Oracle's Elixir match data, keeps only LCK team rows, and creates a one-row-per-
game blue-side view suitable for the proposed ML project.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
BASE_URL = (
    "https://huggingface.co/datasets/Finish-him/todas-as-partidas-lol/resolve/main/"
    "{year}_LoL_esports_match_data_from_OraclesElixir.csv"
)

RAW_DIR = Path("data/raw/oracles_elixir_lck")
PROCESSED_DIR = Path("data/processed")
RAW_TEAM_ROWS = RAW_DIR / "lck_team_rows_2020_2025.csv"
PROCESSED_BLUE_VIEW = PROCESSED_DIR / "lck_blue_view_early_game_2020_2025.csv"
MANIFEST = PROCESSED_DIR / "lck_dataset_manifest_2020_2025.json"

EARLY_FEATURES = [
    "goldat10", "xpat10", "csat10", "golddiffat10", "xpdiffat10", "csdiffat10",
    "killsat10", "assistsat10", "deathsat10", "opp_killsat10", "opp_assistsat10", "opp_deathsat10",
    "goldat15", "xpat15", "csat15", "golddiffat15", "xpdiffat15", "csdiffat15",
    "killsat15", "assistsat15", "deathsat15", "opp_killsat15", "opp_assistsat15", "opp_deathsat15",
]
META_COLUMNS = [
    "source_year", "gameid", "datacompleteness", "league", "year", "split", "playoffs",
    "date", "game", "patch", "blue_teamname", "red_teamname", "blue_win",
]


def normalize_dict(row: Dict[str, str]) -> Dict[str, str]:
    """Normalize BOM/whitespace in headers and preserve values as strings."""
    out = {}
    for key, value in row.items():
        if key is None:
            continue
        clean_key = key.lstrip("\ufeff").strip()
        if clean_key == "1gameid":  # defensive: seen in noisy ranged curl output, not expected in csv reader
            clean_key = "gameid"
        out[clean_key] = value.strip() if isinstance(value, str) else value
    return out


def stream_year(year: int) -> Iterable[Dict[str, str]]:
    url = BASE_URL.format(year=year)
    request = urllib.request.Request(url, headers={"User-Agent": "team2-lck-feasibility/1.0"})
    with urllib.request.urlopen(request, timeout=180) as resp:
        wrapper = io.TextIOWrapper(resp, encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.DictReader(wrapper)
        for row in reader:
            clean = normalize_dict(row)
            clean["source_year"] = str(year)
            yield clean


def safe_get(row: Dict[str, str], key: str) -> str:
    return row.get(key, "") or ""


def write_outputs() -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_headers: List[str] = []
    team_rows: List[Dict[str, str]] = []
    per_year = {}
    all_columns = set()

    for year in YEARS:
        print(f"[fetch] {year}", file=sys.stderr, flush=True)
        year_total = 0
        year_lck_team = 0
        year_games = set()
        year_complete_games = set()
        start = time.time()
        for row in stream_year(year):
            year_total += 1
            all_columns.update(row.keys())
            if safe_get(row, "league") == "LCK" and safe_get(row, "position") == "team":
                year_lck_team += 1
                year_games.add(safe_get(row, "gameid"))
                if safe_get(row, "datacompleteness") == "complete":
                    year_complete_games.add(safe_get(row, "gameid"))
                team_rows.append(row)
                for key in row.keys():
                    if key not in all_headers:
                        all_headers.append(key)
        per_year[str(year)] = {
            "source_rows_streamed": year_total,
            "lck_team_rows": year_lck_team,
            "lck_unique_games": len(year_games),
            "lck_complete_unique_games": len(year_complete_games),
            "seconds": round(time.time() - start, 2),
            "source_url": BASE_URL.format(year=year),
        }

    # Keep stable output column order: source_year first, then source headers.
    raw_headers = ["source_year"] + [h for h in all_headers if h != "source_year"]
    with RAW_TEAM_ROWS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=raw_headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(team_rows)

    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, str]]] = defaultdict(dict)
    for row in team_rows:
        key = (safe_get(row, "source_year"), safe_get(row, "gameid"))
        grouped[key][safe_get(row, "side")] = row

    processed_rows: List[Dict[str, str]] = []
    skipped = Counter()
    for (source_year, gameid), sides in sorted(grouped.items()):
        blue = sides.get("Blue")
        red = sides.get("Red")
        if not blue:
            skipped["missing_blue"] += 1
            continue
        if safe_get(blue, "datacompleteness") != "complete":
            skipped["incomplete_blue"] += 1
            continue
        out = {
            "source_year": source_year,
            "gameid": gameid,
            "datacompleteness": safe_get(blue, "datacompleteness"),
            "league": safe_get(blue, "league"),
            "year": safe_get(blue, "year"),
            "split": safe_get(blue, "split"),
            "playoffs": safe_get(blue, "playoffs"),
            "date": safe_get(blue, "date"),
            "game": safe_get(blue, "game"),
            "patch": safe_get(blue, "patch"),
            "blue_teamname": safe_get(blue, "teamname"),
            "red_teamname": safe_get(red or {}, "teamname"),
            "blue_win": safe_get(blue, "result"),
        }
        for feature in EARLY_FEATURES:
            out[feature] = safe_get(blue, feature)
        processed_rows.append(out)

    with PROCESSED_BLUE_VIEW.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=META_COLUMNS + EARLY_FEATURES)
        writer.writeheader()
        writer.writerows(processed_rows)

    nonmissing_by_feature = {}
    for feature in EARLY_FEATURES:
        nonmissing = sum(1 for row in processed_rows if row.get(feature) not in (None, ""))
        nonmissing_by_feature[feature] = {
            "nonmissing": nonmissing,
            "missing": len(processed_rows) - nonmissing,
            "coverage_pct": round((nonmissing / len(processed_rows) * 100), 2) if processed_rows else 0,
        }

    complete_feature_rows = sum(
        1 for row in processed_rows
        if all(row.get(feature) not in (None, "") for feature in EARLY_FEATURES)
    )

    manifest = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": {
            "primary_download_page": "https://lol.timsevenhuysen.com/matchdata/",
            "data_dictionary": "https://lol.timsevenhuysen.com/matchdata/match-data-dictionary/",
            "mirror": "https://huggingface.co/datasets/Finish-him/todas-as-partidas-lol/tree/main",
            "yearly_url_template": BASE_URL,
        },
        "years": YEARS,
        "filter": "league == 'LCK' and position == 'team'",
        "raw_team_rows_path": str(RAW_TEAM_ROWS),
        "processed_blue_view_path": str(PROCESSED_BLUE_VIEW),
        "per_year": per_year,
        "raw_lck_team_rows": len(team_rows),
        "processed_blue_view_rows": len(processed_rows),
        "processed_complete_feature_rows": complete_feature_rows,
        "processed_columns": META_COLUMNS + EARLY_FEATURES,
        "candidate_feature_count": len(EARLY_FEATURES),
        "feature_coverage": nonmissing_by_feature,
        "skipped_games": dict(skipped),
        "notes": [
            "Processed data is one row per game from the Blue-side perspective.",
            "Target blue_win is the Blue team result column from Oracle's Elixir team row.",
            "Features are limited to 10/15-minute columns to reduce end-of-game leakage risk.",
            "Champion pick/ban variables are intentionally excluded from the core dataset.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    manifest = write_outputs()
    print(json.dumps({
        "raw_lck_team_rows": manifest["raw_lck_team_rows"],
        "processed_blue_view_rows": manifest["processed_blue_view_rows"],
        "processed_complete_feature_rows": manifest["processed_complete_feature_rows"],
        "candidate_feature_count": manifest["candidate_feature_count"],
        "raw_team_rows_path": manifest["raw_team_rows_path"],
        "processed_blue_view_path": manifest["processed_blue_view_path"],
        "manifest_path": str(MANIFEST),
    }, ensure_ascii=False, indent=2))
