"""Configuration loading for Riot/Supabase project scripts."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_ENV_PATH = Path(".env")


def load_dotenv(path: Path = DEFAULT_ENV_PATH) -> None:
    """Load simple KEY=VALUE pairs into ``os.environ`` without overriding values.

    This intentionally avoids adding a runtime dependency on python-dotenv.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    riot_api_key: str | None
    riot_platform_routing: str = "kr"
    riot_regional_routing: str = "asia"
    riot_queue_id: int = 420
    riot_default_tier: str = "EMERALD"
    riot_default_division: str = "I"
    raw_data_dir: Path = Path("data/raw/riot")
    interim_data_dir: Path = Path("data/interim/riot")
    processed_data_dir: Path = Path("data/processed/riot")
    output_dir: Path = Path("outputs")
    figure_dir: Path = Path("reports/figures")
    model_dir: Path = Path("models")

    @property
    def platform_host(self) -> str:
        return f"{self.riot_platform_routing}.api.riotgames.com"

    @property
    def regional_host(self) -> str:
        return f"{self.riot_regional_routing}.api.riotgames.com"

    def require_riot_api_key(self) -> str:
        if not self.riot_api_key or "your_" in self.riot_api_key:
            raise SystemExit("RIOT_API_KEY is missing. Add it to .env before calling Riot APIs.")
        return self.riot_api_key


def load_settings(env_path: Path = DEFAULT_ENV_PATH) -> Settings:
    load_dotenv(env_path)
    return Settings(
        riot_api_key=_env("RIOT_API_KEY"),
        riot_platform_routing=(_env("RIOT_PLATFORM_ROUTING", "kr") or "kr").lower(),
        riot_regional_routing=(_env("RIOT_REGIONAL_ROUTING", "asia") or "asia").lower(),
        riot_queue_id=_env_int("RIOT_QUEUE_ID", 420),
        riot_default_tier=(_env("RIOT_DEFAULT_TIER", "EMERALD") or "EMERALD").upper(),
        riot_default_division=(_env("RIOT_DEFAULT_DIVISION", "I") or "I").upper(),
        raw_data_dir=Path(_env("RAW_DATA_DIR", "data/raw/riot") or "data/raw/riot"),
        interim_data_dir=Path(_env("INTERIM_DATA_DIR", "data/interim/riot") or "data/interim/riot"),
        processed_data_dir=Path(_env("PROCESSED_DATA_DIR", "data/processed/riot") or "data/processed/riot"),
        output_dir=Path(_env("OUTPUT_DIR", "outputs") or "outputs"),
        figure_dir=Path(_env("FIGURE_DIR", "reports/figures") or "reports/figures"),
        model_dir=Path(_env("MODEL_DIR", "models") or "models"),
    )


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
