"""Local raw/interim JSON storage helpers."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def safe_slug(value: str) -> str:
    allowed = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_", "."}:
            allowed.append(ch)
        else:
            allowed.append("_")
    slug = "".join(allowed).strip("_")
    return slug or stable_hash(value)


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as tmp:
        tmp.write(text)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return read_json(path)


def run_dir(base_dir: Path, run_id: str) -> Path:
    return base_dir / "runs" / safe_slug(run_id)
