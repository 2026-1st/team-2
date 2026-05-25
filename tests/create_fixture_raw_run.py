#!/usr/bin/env python3
"""Create a tiny raw Riot-like fixture run for end-to-end dataset tests."""
from __future__ import annotations

import json
from pathlib import Path

RUN_DIR = Path("data/raw/riot/runs/fixture-e2e")
MATCH_ID = "KR_FIXTURE_1"


def sample_match_detail():
    participants = []
    for participant_id in range(1, 11):
        team_id = 100 if participant_id <= 5 else 200
        participants.append({
            "participantId": participant_id,
            "teamId": team_id,
            "gameEndedInSurrender": team_id == 200,
            "gameEndedInEarlySurrender": False,
        })
    return {
        "metadata": {"matchId": MATCH_ID},
        "info": {
            "queueId": 420,
            "gameDuration": 1810,
            "gameVersion": "16.10.1",
            "participants": participants,
        },
    }


def sample_timeline():
    participant_frames = {}
    for participant_id in range(1, 11):
        blue = participant_id <= 5
        participant_frames[str(participant_id)] = {
            "totalGold": 1000 if blue else 900,
            "minionsKilled": 10 if blue else 8,
            "jungleMinionsKilled": 1 if blue else 0,
            "level": 6 if blue else 5,
        }
    return {
        "info": {
            "frames": [
                {
                    "timestamp": 600000,
                    "events": [
                        {"timestamp": 100000, "type": "CHAMPION_KILL", "killerId": 1, "victimId": 6},
                        {
                            "timestamp": 300000,
                            "type": "BUILDING_KILL",
                            "buildingType": "TOWER_BUILDING",
                            "killerId": 2,
                            "teamId": 200,
                        },
                        {
                            "timestamp": 500000,
                            "type": "ELITE_MONSTER_KILL",
                            "monsterType": "DRAGON",
                            "killerTeamId": 100,
                        },
                        {
                            "timestamp": 650000,
                            "type": "ELITE_MONSTER_KILL",
                            "monsterType": "RIFTHERALD",
                            "killerTeamId": 200,
                        },
                        {"timestamp": 550000, "type": "WARD_PLACED", "creatorId": 7},
                        {"timestamp": 560000, "type": "WARD_KILL", "killerId": 3},
                    ],
                },
                {"timestamp": 900000, "participantFrames": participant_frames, "events": []},
            ]
        }
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    write_json(RUN_DIR / "matches" / f"{MATCH_ID}.json", sample_match_detail())
    write_json(RUN_DIR / "timelines" / f"{MATCH_ID}.json", sample_timeline())
    write_json(
        RUN_DIR / "manifest.json",
        {
            "status": "fixture",
            "run_id": RUN_DIR.name,
            "match_ids": [MATCH_ID],
            "counts": {"unique_match_ids": 1, "match_details": 1, "timelines": 1},
        },
    )
    print(f"fixture_raw_run_created: {RUN_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
