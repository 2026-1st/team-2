"""Minimal Riot API client for League-V4, Summoner-V4, and Match-V5."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


class RiotAPIError(RuntimeError):
    """Raised when Riot API returns a non-retryable error."""

    def __init__(self, status: int | None, message: str, endpoint: str) -> None:
        self.status = status
        self.endpoint = endpoint
        super().__init__(f"Riot API error status={status} endpoint={endpoint}: {message}")


@dataclass(frozen=True)
class RiotClient:
    api_key: str
    platform_host: str = "kr.api.riotgames.com"
    regional_host: str = "asia.api.riotgames.com"
    user_agent: str = "team2-surrender-prediction/0.1"
    timeout: int = 30
    max_retries: int = 4
    min_interval_sec: float = 0.08

    def _build_url(self, host: str, path: str, params: Mapping[str, Any] | None = None) -> str:
        query = ""
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            query = "?" + urllib.parse.urlencode(clean_params)
        return f"https://{host}{path}{query}"

    def _get_json(self, host: str, path: str, params: Mapping[str, Any] | None = None) -> Any:
        url = self._build_url(host, path, params)
        request = urllib.request.Request(
            url,
            headers={
                "X-Riot-Token": self.api_key,
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            if self.min_interval_sec > 0:
                time.sleep(self.min_interval_sec)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as exc:
                status = exc.code
                endpoint = path.split("?", 1)[0]
                body = exc.read().decode("utf-8", errors="replace")[:500]
                if status == 429 or 500 <= status < 600:
                    retry_after = exc.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 30)
                    last_error = RiotAPIError(status, body or exc.reason, endpoint)
                    if attempt < self.max_retries:
                        time.sleep(wait)
                        continue
                raise RiotAPIError(status, body or exc.reason, endpoint) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                raise RiotAPIError(None, str(exc), path) from exc
        raise RiotAPIError(None, str(last_error), path)

    def league_entries(
        self,
        tier: str,
        division: str,
        page: int = 1,
        queue: str = "RANKED_SOLO_5x5",
    ) -> list[dict[str, Any]]:
        path = f"/lol/league/v4/entries/{queue}/{tier.upper()}/{division.upper()}"
        return self._get_json(self.platform_host, path, {"page": page})

    def summoner_by_encrypted_id(self, encrypted_summoner_id: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(encrypted_summoner_id, safe="")
        return self._get_json(self.platform_host, f"/lol/summoner/v4/summoners/{encoded}")

    def match_ids_by_puuid(
        self,
        puuid: str,
        queue_id: int = 420,
        match_type: str = "ranked",
        start: int = 0,
        count: int = 20,
    ) -> list[str]:
        encoded = urllib.parse.quote(puuid, safe="")
        return self._get_json(
            self.regional_host,
            f"/lol/match/v5/matches/by-puuid/{encoded}/ids",
            {"queue": queue_id, "type": match_type, "start": start, "count": count},
        )

    def match_detail(self, match_id: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(match_id, safe="")
        return self._get_json(self.regional_host, f"/lol/match/v5/matches/{encoded}")

    def match_timeline(self, match_id: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(match_id, safe="")
        return self._get_json(self.regional_host, f"/lol/match/v5/matches/{encoded}/timeline")
