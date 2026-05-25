from __future__ import annotations

import unittest

from team2_surrender.features import match_to_team_rows
from team2_surrender.labels import exclusion_reason, team_surrender_labels


def sample_match_detail(*, early_surrender: bool = False, duration: int = 1800):
    participants = []
    for participant_id in range(1, 11):
        team_id = 100 if participant_id <= 5 else 200
        participants.append({
            "participantId": participant_id,
            "teamId": team_id,
            "win": team_id == 100,
            "gameEndedInSurrender": True,
            "gameEndedInEarlySurrender": early_surrender,
        })
    return {
        "metadata": {"matchId": "KR_TEST_1"},
        "info": {
            "queueId": 420,
            "gameDuration": duration,
            "gameVersion": "16.10.1",
            "participants": participants,
            "teams": [{"teamId": 100, "win": True}, {"teamId": 200, "win": False}],
        },
    }


def sample_timeline():
    participant_frames = {}
    for participant_id in range(1, 11):
        blue = participant_id <= 5
        participant_frames[str(participant_id)] = {
            "totalGold": 1000 if blue else 900,
            "minionsKilled": 10 if blue else 8,
            "jungleMinionsKilled": 0,
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
                        {"timestamp": 550000, "type": "WARD_PLACED", "creatorId": 7, "wardType": "YELLOW_TRINKET"},
                        {"timestamp": 555000, "type": "WARD_PLACED", "creatorId": 7, "wardType": "UNDEFINED"},
                        {"timestamp": 560000, "type": "WARD_KILL", "killerId": 3, "wardType": "CONTROL_WARD"},
                        {"timestamp": 565000, "type": "WARD_KILL", "killerId": 3, "wardType": "UNDEFINED"},
                    ],
                },
                {"timestamp": 900000, "participantFrames": participant_frames, "events": []},
            ]
        }
    }


class LabelFeatureTests(unittest.TestCase):
    def test_team_surrender_label_is_team_level(self):
        labels = team_surrender_labels(sample_match_detail())
        self.assertFalse(labels[100])
        self.assertTrue(labels[200])

    def test_excludes_early_surrender_and_short_games(self):
        self.assertEqual(exclusion_reason(sample_match_detail(early_surrender=True)), "early_surrender_or_remake")
        self.assertEqual(exclusion_reason(sample_match_detail(duration=899)), "game_duration_under_15min")

    def test_extracts_team_perspective_15min_features(self):
        rows, reason = match_to_team_rows(sample_match_detail(), sample_timeline())
        self.assertIsNone(reason)
        self.assertEqual(len(rows), 2)
        blue = next(row for row in rows if row["team_id"] == 100)
        red = next(row for row in rows if row["team_id"] == 200)

        self.assertEqual(blue["gold_diff_15"], 500)
        self.assertEqual(red["gold_diff_15"], -500)
        self.assertEqual(blue["cs_diff_15"], 10)
        self.assertEqual(blue["avg_level_diff_15"], 1.0)
        self.assertEqual(blue["kill_diff_15"], 1)
        self.assertEqual(blue["tower_diff_15"], 1)
        self.assertEqual(blue["dragon_diff_15"], 1)
        self.assertEqual(blue["first_blood"], 1)
        self.assertEqual(red["first_blood"], -1)
        self.assertEqual(blue["first_tower"], 1)
        self.assertEqual(blue["ward_placed_diff_15"], -1)
        self.assertEqual(blue["ward_kill_diff_15"], 1)
        self.assertFalse(blue["team_surrendered"])
        self.assertTrue(red["team_surrendered"])


if __name__ == "__main__":
    unittest.main()
