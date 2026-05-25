"""15-minute team feature extraction from Riot Match-V5 timelines."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .labels import TEAM_IDS, exclusion_reason, game_duration_sec, queue_id, team_surrender_labels

CUTOFF_MS = 15 * 60 * 1000
FEATURE_VERSION = "v1_15min"
PARTICIPANT_TEAM = {str(i): 100 if i <= 5 else 200 for i in range(1, 11)}


def _team_for_participant(participant_id: int | str | None) -> int | None:
    if participant_id is None:
        return None
    return PARTICIPANT_TEAM.get(str(participant_id))


def _opponent(team_id: int) -> int:
    return 200 if team_id == 100 else 100


def _destroyed_building_owner(event: dict[str, Any]) -> int | None:
    try:
        team_id = int(event.get("teamId"))
    except (TypeError, ValueError):
        return None
    return team_id if team_id in TEAM_IDS else None


def _event_actor_team(event: dict[str, Any]) -> int | None:
    """Return the team credited for an event.

    Timeline events use different fields by event type. In BUILDING_KILL,
    ``teamId`` is the owner of the destroyed building, so the credited team is
    the killer team, not ``teamId``.
    """
    etype = event.get("type")
    if etype == "BUILDING_KILL":
        killer_team = _team_for_participant(event.get("killerId"))
        if killer_team in TEAM_IDS:
            return killer_team
        owner = _destroyed_building_owner(event)
        return _opponent(owner) if owner in TEAM_IDS else None
    if etype == "ELITE_MONSTER_KILL":
        try:
            killer_team_id = int(event.get("killerTeamId"))
            if killer_team_id in TEAM_IDS:
                return killer_team_id
        except (TypeError, ValueError):
            pass
        return _team_for_participant(event.get("killerId"))
    if etype == "WARD_PLACED":
        return _team_for_participant(event.get("creatorId"))
    if etype in {"CHAMPION_KILL", "WARD_KILL"}:
        return _team_for_participant(event.get("killerId"))
    return _team_for_participant(event.get("participantId"))


def _first_frame_at_or_after(timeline: dict[str, Any], cutoff_ms: int = CUTOFF_MS) -> dict[str, Any] | None:
    frames = timeline.get("info", {}).get("frames", [])
    if not frames:
        return None
    eligible = [frame for frame in frames if int(frame.get("timestamp", 0)) >= cutoff_ms]
    if eligible:
        return min(eligible, key=lambda frame: int(frame.get("timestamp", 0)))
    return None


def _iter_events_until(timeline: dict[str, Any], cutoff_ms: int = CUTOFF_MS):
    for frame in timeline.get("info", {}).get("frames", []):
        for event in frame.get("events", []):
            if int(event.get("timestamp", 0)) <= cutoff_ms:
                yield event


def _diff(values: dict[int, float], team_id: int) -> float:
    opponent = _opponent(team_id)
    return values.get(team_id, 0) - values.get(opponent, 0)


def _sign_for_team(winning_team: int | None, team_id: int) -> int:
    if winning_team not in TEAM_IDS:
        return 0
    return 1 if winning_team == team_id else -1


def extract_team_rows(match_detail: dict[str, Any], timeline: dict[str, Any], feature_version: str = FEATURE_VERSION) -> list[dict[str, Any]]:
    """Build two team rows for an eligible match.

    Raises ValueError if the match cannot be converted because the 15-minute frame
    is missing. Match-level exclusion rules should be checked before calling.
    """
    frame15 = _first_frame_at_or_after(timeline)
    if frame15 is None:
        raise ValueError("missing_15min_frame")

    participant_frames = frame15.get("participantFrames", {})
    if not participant_frames:
        raise ValueError("missing_participant_frames")

    totals = {
        "gold": defaultdict(int),
        "cs": defaultdict(int),
        "level_sum": defaultdict(float),
        "level_count": defaultdict(int),
    }
    for participant_id, pdata in participant_frames.items():
        team = _team_for_participant(participant_id)
        if team not in TEAM_IDS:
            continue
        totals["gold"][team] += int(pdata.get("totalGold") or 0)
        totals["cs"][team] += int(pdata.get("minionsKilled") or 0) + int(pdata.get("jungleMinionsKilled") or 0)
        totals["level_sum"][team] += float(pdata.get("level") or 0)
        totals["level_count"][team] += 1

    if any(totals["level_count"].get(team, 0) == 0 for team in TEAM_IDS):
        raise ValueError("missing_team_participant_frames")

    avg_level = {
        team: totals["level_sum"][team] / totals["level_count"][team]
        for team in TEAM_IDS
    }

    counts = {
        "kills": defaultdict(int),
        "towers": defaultdict(int),
        "dragons": defaultdict(int),
        "rift_heralds": defaultdict(int),
        "wards_placed": defaultdict(int),
        "wards_killed": defaultdict(int),
    }
    first_blood_team = None
    first_tower_team = None
    first_kill_ts = None
    first_tower_ts = None

    for event in _iter_events_until(timeline):
        etype = event.get("type")
        team = _event_actor_team(event)
        if team not in TEAM_IDS:
            continue
        timestamp = int(event.get("timestamp", 0))
        if etype == "CHAMPION_KILL":
            counts["kills"][team] += 1
            if first_kill_ts is None or timestamp < first_kill_ts:
                first_kill_ts = timestamp
                first_blood_team = team
        elif etype == "BUILDING_KILL" and event.get("buildingType") == "TOWER_BUILDING":
            counts["towers"][team] += 1
            if first_tower_ts is None or timestamp < first_tower_ts:
                first_tower_ts = timestamp
                first_tower_team = team
        elif etype == "ELITE_MONSTER_KILL":
            monster_type = event.get("monsterType")
            if monster_type == "DRAGON":
                counts["dragons"][team] += 1
            elif monster_type == "RIFTHERALD":
                counts["rift_heralds"][team] += 1
        elif etype == "WARD_PLACED":
            if event.get("wardType") != "UNDEFINED":
                counts["wards_placed"][team] += 1
        elif etype == "WARD_KILL":
            if event.get("wardType") != "UNDEFINED":
                counts["wards_killed"][team] += 1

    labels = team_surrender_labels(match_detail)
    info = match_detail.get("info", {})
    metadata = match_detail.get("metadata", {})
    match_id = metadata.get("matchId") or info.get("gameId")
    qid = queue_id(match_detail)
    duration = game_duration_sec(match_detail)
    version = info.get("gameVersion")

    rows: list[dict[str, Any]] = []
    for team_id in TEAM_IDS:
        rows.append({
            "match_id": match_id,
            "team_id": team_id,
            "feature_version": feature_version,
            "team_surrendered": bool(labels[team_id]),
            "queue_id": qid,
            "game_version": version,
            "game_duration_sec": duration,
            "collected_at": None,
            "gold_diff_15": int(_diff(totals["gold"], team_id)),
            "kill_diff_15": int(_diff(counts["kills"], team_id)),
            "tower_diff_15": int(_diff(counts["towers"], team_id)),
            "dragon_diff_15": int(_diff(counts["dragons"], team_id)),
            "rift_herald_diff_15": int(_diff(counts["rift_heralds"], team_id)),
            "cs_diff_15": int(_diff(totals["cs"], team_id)),
            "avg_level_diff_15": round(float(_diff(avg_level, team_id)), 3),
            "first_blood": _sign_for_team(first_blood_team, team_id),
            "first_tower": _sign_for_team(first_tower_team, team_id),
            "ward_placed_diff_15": int(_diff(counts["wards_placed"], team_id)),
            "ward_kill_diff_15": int(_diff(counts["wards_killed"], team_id)),
        })
    return rows


def match_to_team_rows(match_detail: dict[str, Any], timeline: dict[str, Any], required_queue_id: int = 420) -> tuple[list[dict[str, Any]], str | None]:
    reason = exclusion_reason(match_detail, required_queue_id=required_queue_id)
    if reason:
        return [], reason
    try:
        return extract_team_rows(match_detail, timeline), None
    except ValueError as exc:
        return [], str(exc)
