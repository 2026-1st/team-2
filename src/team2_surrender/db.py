"""Direct Supabase/Postgres connection helpers."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

from .config import load_dotenv


def project_ref_from_supabase_url(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc or parsed.path
    if not host:
        return None
    return host.split(".")[0]


def build_conn_kwargs() -> dict[str, object] | None:
    """Build psycopg2 kwargs from SUPABASE_DB_URL/DATABASE_URL or password."""
    load_dotenv()
    explicit = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if explicit:
        parsed = urlparse(explicit)
        if parsed.scheme not in {"postgresql", "postgres"}:
            raise SystemExit("SUPABASE_DB_URL must start with postgresql:// or postgres://")
        if not parsed.hostname or not parsed.username or parsed.password is None:
            raise SystemExit(
                "SUPABASE_DB_URL is missing hostname, username, or password. "
                "Copy the full connection string from Supabase."
            )
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "dbname": parsed.path.lstrip("/") or "postgres",
            "user": unquote(parsed.username),
            "password": unquote(parsed.password),
            "sslmode": "require",
        }

    password = os.getenv("SUPABASE_DB_PASSWORD")
    project_ref = project_ref_from_supabase_url(os.getenv("SUPABASE_URL", ""))
    if password and project_ref:
        return {
            "host": f"db.{project_ref}.supabase.co",
            "port": 5432,
            "dbname": "postgres",
            "user": "postgres",
            "password": password,
            "sslmode": "require",
        }
    return None


def require_conn_kwargs() -> dict[str, object]:
    kwargs = build_conn_kwargs()
    if kwargs:
        return kwargs
    raise SystemExit(
        "Missing database connection info. Add SUPABASE_DB_URL or SUPABASE_DB_PASSWORD to .env."
    )
