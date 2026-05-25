"""Label and eligibility helpers for Riot match details."""
from __future__ import annotations

from typing import Any


TEAM_IDS = (100, 200)


def game_duration_sec(match_detail: dict[str, Any]) -> int:
    info = match_detail.get("info", {})
    duration = info.get("gameDuration")
    return int(duration or 0)


def queue_id(match_detail: dict[str, Any]) -> int | None:
    value = match_detail.get("info", {}).get("queueId")
    return int(value) if value is not None else None


def exclusion_reason(match_detail: dict[str, Any], required_queue_id: int = 420, min_duration_sec: int = 900) -> str | None:
    qid = queue_id(match_detail)
    if qid != required_queue_id:
        return f"queue_id_{qid}_not_{required_queue_id}"
    if game_duration_sec(match_detail) < min_duration_sec:
        return "game_duration_under_15min"
    participants = match_detail.get("info", {}).get("participants", [])
    if any(p.get("gameEndedInEarlySurrender") for p in participants):
        return "early_surrender_or_remake"
    return None


def team_win_map(match_detail: dict[str, Any]) -> dict[int, bool | None]:
    """Return team win status keyed by team id when available."""
    wins: dict[int, bool | None] = {team_id: None for team_id in TEAM_IDS}

    # Match-V5 team objects usually contain the most direct team-level result.
    for team in match_detail.get("info", {}).get("teams", []) or []:
        try:
            team_id = int(team.get("teamId"))
        except (TypeError, ValueError):
            continue
        if team_id in wins and "win" in team:
            wins[team_id] = bool(team.get("win"))

    # Participant rows also include win in Match-V5; use them as fallback.
    for participant in match_detail.get("info", {}).get("participants", []) or []:
        try:
            team_id = int(participant.get("teamId"))
        except (TypeError, ValueError):
            continue
        if team_id in wins and wins[team_id] is None and "win" in participant:
            wins[team_id] = bool(participant.get("win"))

    return wins


def team_surrender_labels(match_detail: dict[str, Any]) -> dict[int, bool]:
    """Return team-level surrender-defeat labels keyed by Riot team id.

    Positive label means this team ultimately **lost** via normal surrender. Riot's
    ``gameEndedInSurrender`` can appear on participant rows for a surrender-ended
    game, so the label must combine surrender-ended status with losing-team status
    to avoid marking the winning team as surrendered.
    """
    participants = match_detail.get("info", {}).get("participants", [])
    wins = team_win_map(match_detail)
    surrender_seen = {team_id: False for team_id in TEAM_IDS}
    for participant in participants:
        try:
            team_id = int(participant.get("teamId"))
        except (TypeError, ValueError):
            continue
        if team_id in surrender_seen and bool(participant.get("gameEndedInSurrender")):
            surrender_seen[team_id] = True

    labels = {team_id: False for team_id in TEAM_IDS}
    for team_id in TEAM_IDS:
        won = wins.get(team_id)
        # If win is missing, keep the conservative old behavior for robustness,
        # but real Match-V5 data should include win and therefore only losing
        # teams become positive.
        labels[team_id] = surrender_seen[team_id] if won is None else (surrender_seen[team_id] and not won)
    return labels
