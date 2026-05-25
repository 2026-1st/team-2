"""Dataset constants shared by scripts."""
from __future__ import annotations

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

PUBLIC_FORBIDDEN_COLUMNS = {
    "puuid",
    "summonerId",
    "summonerName",
    "riotIdGameName",
    "riotIdTagline",
    "RIOT_API_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
}
