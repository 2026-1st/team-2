#!/usr/bin/env python3
"""Check repository text files for accidentally committed API keys/secrets."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".omx",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "data/raw",
    "data/interim",
    "data/processed",
    "models",
    "outputs",
    "reports/figures",
}
DEFAULT_EXCLUDE_FILES = {
    ".env",
    ".DS_Store",
}
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".csv",
    ".env",
    ".example",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PATTERNS = [
    ("riot_api_key", re.compile(r"RGAPI-[A-Za-z0-9_-]{25,}")),
    ("supabase_secret_key", re.compile(r"sb_secret_[A-Za-z0-9_-]{20,}")),
    ("supabase_publishable_key", re.compile(r"sb_publishable_[A-Za-z0-9_-]{20,}")),
    # JWT-like legacy Supabase service-role keys. Keep conservative to reduce false positives.
    ("jwt_like_secret", re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
]
ALLOWLIST_FRAGMENTS = {
    "RGAPI-your_riot_api_key_here",
    "RGAPI-...",
    "sb_secret_...",
    "sb_publishable_...",
    "your_supabase_anon_key_here",
    "your_supabase_service_role_key_here",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    rel_str = str(rel)
    if path.name in DEFAULT_EXCLUDE_FILES:
        return True
    parts = rel.parts
    for idx in range(1, len(parts) + 1):
        prefix = "/".join(parts[:idx])
        if prefix in DEFAULT_EXCLUDE_DIRS:
            return True
    return rel_str.endswith(".docx") or rel_str.endswith(".png") or rel_str.endswith(".joblib")


def is_text_candidate(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name in {"README", "LICENSE"}


def allowed(match: str) -> bool:
    return any(fragment in match for fragment in ALLOWLIST_FRAGMENTS)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or is_excluded(path, root) or not is_text_candidate(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS:
                for match in pattern.findall(line):
                    if allowed(match):
                        continue
                    findings.append({"file": str(path.relative_to(root)), "line": line_no, "type": name})
    if findings:
        print("secret_scan_failed")
        for item in findings[:50]:
            print(f" - {item['file']}:{item['line']} {item['type']}")
        if len(findings) > 50:
            print(f"... and {len(findings) - 50} more")
        return 1
    print("secret_scan_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
