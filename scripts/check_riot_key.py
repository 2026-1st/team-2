#!/usr/bin/env python3
"""Check whether the configured Riot API key can access a small League-V4 request."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team2_surrender.config import load_settings  # noqa: E402
from team2_surrender.riot_client import RiotAPIError, RiotClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", default=None)
    parser.add_argument("--division", default=None)
    parser.add_argument("--page", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()
    api_key = settings.require_riot_api_key()
    tier = (args.tier or settings.riot_default_tier).upper()
    division = (args.division or settings.riot_default_division).upper()
    client = RiotClient(api_key=api_key, platform_host=settings.platform_host, regional_host=settings.regional_host, max_retries=0)
    try:
        entries = client.league_entries(tier=tier, division=division, page=args.page)
    except RiotAPIError as exc:
        print(f"riot_key_check_failed: status={exc.status} endpoint={exc.endpoint}")
        if exc.status == 401:
            print("hint: Riot API key is invalid, expired, or not active. Reissue it and update RIOT_API_KEY in .env.")
        elif exc.status == 403:
            print("hint: Riot API key is recognized but forbidden for this request or region.")
        return 2
    print("riot_key_check_ok")
    print(f"platform_host: {settings.platform_host}")
    print(f"sample_rows_returned: {len(entries) if isinstance(entries, list) else 'unknown'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
