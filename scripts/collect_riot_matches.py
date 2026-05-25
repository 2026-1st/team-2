#!/usr/bin/env python3
"""Collect a small, resumable raw Riot API sample for surrender prediction.

Raw outputs are written below data/raw/riot/runs/<run-id>/ and are ignored by git.
The manifest intentionally stores counts and safe match ids only, not PUUIDs or
summoner identifiers.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Allow running without installing the package.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team2_surrender.config import ensure_dirs, load_settings
from team2_surrender.riot_client import RiotAPIError, RiotClient
from team2_surrender.storage import atomic_write_json, read_json_if_exists, run_dir, safe_slug, stable_hash, utc_now_iso


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", default=None, help="Rank tier, e.g. EMERALD")
    parser.add_argument("--division", default=None, help="Rank division, e.g. I")
    parser.add_argument("--pages", type=int, default=1, help="League-V4 pages to scan")
    parser.add_argument("--max-seeds", type=int, default=10, help="Maximum seed accounts to use")
    parser.add_argument("--matches-per-puuid", type=int, default=5, help="Match ids to request per seed")
    parser.add_argument("--max-unique-matches", type=int, default=10, help="Maximum unique matches to fetch detail/timeline for")
    parser.add_argument("--start", type=int, default=0, help="Match-V5 start offset per PUUID")
    parser.add_argument("--run-id", default=None, help="Stable run id for resume; default timestamp")
    parser.add_argument("--resume", action="store_true", help="Reuse cached JSON files when present")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and print planned paths without network calls")
    return parser.parse_args()


def load_or_fetch(path: Path, resume: bool, fetcher):
    if resume:
        cached = read_json_if_exists(path)
        if cached is not None:
            return cached, True
    payload = fetcher()
    atomic_write_json(path, payload)
    return payload, False


def entry_puuid(entry: dict[str, Any]) -> str | None:
    value = entry.get("puuid")
    return str(value) if value else None


def entry_summoner_id(entry: dict[str, Any]) -> str | None:
    value = entry.get("summonerId")
    return str(value) if value else None


def main() -> int:
    args = parse_args()
    settings = load_settings()
    tier = (args.tier or settings.riot_default_tier).upper()
    division = (args.division or settings.riot_default_division).upper()
    run_id = args.run_id or utc_now_iso().replace(":", "").replace("+", "Z")
    base_run_dir = run_dir(settings.raw_data_dir, run_id)

    planned_dirs = [
        base_run_dir / "league_entries",
        base_run_dir / "summoners",
        base_run_dir / "match_ids",
        base_run_dir / "matches",
        base_run_dir / "timelines",
    ]
    ensure_dirs(planned_dirs)

    config_summary = {
        "run_id": run_id,
        "tier": tier,
        "division": division,
        "pages": args.pages,
        "max_seeds": args.max_seeds,
        "matches_per_puuid": args.matches_per_puuid,
        "max_unique_matches": args.max_unique_matches,
        "queue_id": settings.riot_queue_id,
        "platform_host": settings.platform_host,
        "regional_host": settings.regional_host,
        "run_dir": str(base_run_dir),
        "riot_api_key_present": bool(settings.riot_api_key and "your_" not in settings.riot_api_key),
    }
    if args.dry_run:
        atomic_write_json(base_run_dir / "dry_run_plan.json", config_summary)
        print("dry_run_complete: no network calls made")
        print(f"run_dir: {base_run_dir}")
        print(f"riot_api_key_present: {config_summary['riot_api_key_present']}")
        return 0

    api_key = settings.require_riot_api_key()
    client = RiotClient(api_key=api_key, platform_host=settings.platform_host, regional_host=settings.regional_host)

    manifest: dict[str, Any] = {
        "started_at": utc_now_iso(),
        "run_id": run_id,
        "params": {k: v for k, v in config_summary.items() if k != "riot_api_key_present"},
        "counts": {
            "league_entry_pages": 0,
            "seed_entries": 0,
            "puuids_resolved": 0,
            "unique_match_ids": 0,
            "match_details": 0,
            "timelines": 0,
        },
        "match_ids": [],
        "errors": [],
    }

    try:
        entries: list[dict[str, Any]] = []
        for page in range(1, args.pages + 1):
            path = base_run_dir / "league_entries" / f"{safe_slug(tier)}_{safe_slug(division)}_page_{page}.json"
            payload, cached = load_or_fetch(path, args.resume, lambda page=page: client.league_entries(tier=tier, division=division, page=page))
            manifest["counts"]["league_entry_pages"] += 1
            page_entries = payload if isinstance(payload, list) else []
            entries.extend(page_entries)
            print(f"league_entries page={page} rows={len(page_entries)} cached={cached}")

        seeds = entries[: max(args.max_seeds, 0)]
        manifest["counts"]["seed_entries"] = len(seeds)

        puuids: list[str] = []
        for idx, entry in enumerate(seeds, start=1):
            puuid = entry_puuid(entry)
            if not puuid:
                summoner_id = entry_summoner_id(entry)
                if not summoner_id:
                    manifest["errors"].append({"stage": "resolve_puuid", "seed_index": idx, "error": "missing_summoner_id_and_puuid"})
                    continue
                summoner_path = base_run_dir / "summoners" / f"seed_{idx:04d}_{stable_hash(summoner_id)}.json"
                summoner, cached = load_or_fetch(
                    summoner_path,
                    args.resume,
                    lambda summoner_id=summoner_id: client.summoner_by_encrypted_id(summoner_id),
                )
                puuid = summoner.get("puuid") if isinstance(summoner, dict) else None
                print(f"summoner seed={idx} puuid_resolved={bool(puuid)} cached={cached}")
            if puuid:
                puuids.append(str(puuid))

        # Preserve order and remove duplicate seed PUUIDs without logging them.
        unique_puuids = list(dict.fromkeys(puuids))
        manifest["counts"]["puuids_resolved"] = len(unique_puuids)

        unique_match_ids: list[str] = []
        seen_matches: set[str] = set()
        for idx, puuid in enumerate(unique_puuids, start=1):
            if len(unique_match_ids) >= args.max_unique_matches:
                break
            path = base_run_dir / "match_ids" / f"seed_{idx:04d}_{stable_hash(puuid)}.json"
            ids, cached = load_or_fetch(
                path,
                args.resume,
                lambda puuid=puuid: client.match_ids_by_puuid(
                    puuid,
                    queue_id=settings.riot_queue_id,
                    start=args.start,
                    count=args.matches_per_puuid,
                ),
            )
            ids = ids if isinstance(ids, list) else []
            added = 0
            for match_id in ids:
                if match_id not in seen_matches:
                    seen_matches.add(match_id)
                    unique_match_ids.append(match_id)
                    added += 1
                    if len(unique_match_ids) >= args.max_unique_matches:
                        break
            print(f"match_ids seed={idx} returned={len(ids)} added={added} cached={cached}")

        manifest["counts"]["unique_match_ids"] = len(unique_match_ids)
        manifest["match_ids"] = unique_match_ids

        for idx, match_id in enumerate(unique_match_ids, start=1):
            detail_path = base_run_dir / "matches" / f"{safe_slug(match_id)}.json"
            timeline_path = base_run_dir / "timelines" / f"{safe_slug(match_id)}.json"
            _, detail_cached = load_or_fetch(detail_path, args.resume, lambda match_id=match_id: client.match_detail(match_id))
            manifest["counts"]["match_details"] += 1
            _, timeline_cached = load_or_fetch(timeline_path, args.resume, lambda match_id=match_id: client.match_timeline(match_id))
            manifest["counts"]["timelines"] += 1
            print(f"match {idx}/{len(unique_match_ids)} id={match_id} detail_cached={detail_cached} timeline_cached={timeline_cached}")

    except RiotAPIError as exc:
        manifest["errors"].append({"stage": "riot_api", "status": exc.status, "endpoint": exc.endpoint, "error": str(exc)[:500]})
        manifest["finished_at"] = utc_now_iso()
        manifest["status"] = "failed"
        atomic_write_json(base_run_dir / "manifest.json", manifest)
        print(f"collection_failed: status={exc.status} endpoint={exc.endpoint}", file=sys.stderr)
        return 2

    manifest["finished_at"] = utc_now_iso()
    manifest["status"] = "complete"
    atomic_write_json(base_run_dir / "manifest.json", manifest)
    print("collection_complete")
    print(f"run_dir: {base_run_dir}")
    print("counts:", manifest["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
