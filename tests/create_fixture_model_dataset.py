#!/usr/bin/env python3
"""Create a deterministic processed dataset big enough for model smoke tests."""
from __future__ import annotations

import csv
import random
from pathlib import Path

from team2_surrender.dataset import TEAM_FEATURE_COLUMNS

OUT = Path("data/processed/riot/fixture_model_team_features.csv")


def main() -> int:
    random.seed(42)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for match_num in range(1, 61):
        # Strong but imperfect signal: large negative gold/kill diffs often surrender.
        blue_adv = random.randint(-4500, 4500)
        blue_kills = random.randint(-10, 10)
        blue_towers = random.randint(-4, 4)
        blue_dragons = random.randint(-2, 2)
        blue_heralds = random.randint(-1, 1)
        blue_cs = int(blue_adv / 120) + random.randint(-20, 20)
        blue_level = round(blue_adv / 2500 + random.uniform(-0.5, 0.5), 3)
        score = blue_adv + blue_kills * 250 + blue_towers * 500 + random.randint(-1200, 1200)
        blue_surrenders = score < -1800
        match_id = f"KR_MODEL_FIXTURE_{match_num}"
        for team_id, sign in [(100, 1), (200, -1)]:
            surrender = blue_surrenders if team_id == 100 else (score > 1800)
            rows.append({
                "match_id": match_id,
                "team_id": team_id,
                "feature_version": "v1_15min",
                "team_surrendered": surrender,
                "queue_id": 420,
                "game_version": "16.10.1",
                "game_duration_sec": 1500 + random.randint(0, 900),
                "collected_at": "2026-05-14T00:00:00+00:00",
                "gold_diff_15": sign * blue_adv,
                "kill_diff_15": sign * blue_kills,
                "tower_diff_15": sign * blue_towers,
                "dragon_diff_15": sign * blue_dragons,
                "rift_herald_diff_15": sign * blue_heralds,
                "cs_diff_15": sign * blue_cs,
                "avg_level_diff_15": sign * blue_level,
                "first_blood": 1 if sign * blue_kills > 0 else (-1 if sign * blue_kills < 0 else 0),
                "first_tower": 1 if sign * blue_towers > 0 else (-1 if sign * blue_towers < 0 else 0),
                "ward_placed_diff_15": sign * random.randint(-12, 12),
                "ward_kill_diff_15": sign * random.randint(-6, 6),
            })
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEAM_FEATURE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"fixture_model_dataset_created: {OUT} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
