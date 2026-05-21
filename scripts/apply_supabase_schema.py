#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "의존성 누락: psycopg2. psycopg2-binary를 설치하거나 psycopg2가 있는 Python 환경에서 실행하세요."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team2_surrender.config import load_dotenv
from team2_surrender.db import require_conn_kwargs

DEFAULT_SCHEMA_FILE = Path("docs/supabase_schema.sql")
REQUIRED_TABLES = ("collection_runs", "riot_matches", "team_features")



def apply_schema(schema_file: Path, dry_run: bool = False) -> None:
    if not schema_file.exists():
        raise SystemExit(f"스키마 파일을 찾을 수 없습니다: {schema_file}")

    sql = schema_file.read_text(encoding="utf-8")
    if dry_run:
        print(f"dry_run: 스키마 파일 확인 완료 ({schema_file}, {len(sql)} bytes)")
        print("dry_run: 데이터베이스 연결은 열지 않았습니다")
        return

    conn_kwargs = require_conn_kwargs()
    print("connection_info: 설정됨 (값 숨김)")
    print(f"db_host: {conn_kwargs['host']}")
    print(f"schema_file: {schema_file}")

    try:
        with psycopg2.connect(**conn_kwargs) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    """
                    select table_name
                    from information_schema.tables
                    where table_schema = 'public'
                      and table_name = any(%s)
                    order by table_name
                    """,
                    (list(REQUIRED_TABLES),),
                )
                found = [row[0] for row in cur.fetchall()]
    except psycopg2.OperationalError as exc:
        message = str(exc)
        if "No route to host" in message or "Network is unreachable" in message:
            raise SystemExit(
                "Supabase Direct connection에 연결할 수 없습니다. Direct connection이 IPv6로 해석되지만 "
                "로컬 네트워크에 IPv6 경로가 없을 때 자주 발생합니다. SUPABASE_DB_URL을 "
                "Supabase Dashboard > Connect > Connection Pooling / Session pooler 연결 문자열로 "
                "교체한 뒤 이 스크립트를 다시 실행하세요."
            ) from exc
        raise

    missing = sorted(set(REQUIRED_TABLES) - set(found))
    print("tables_found:", ", ".join(found) if found else "없음")
    if missing:
        raise SystemExit("schema_apply_incomplete: 누락된 테이블: " + ", ".join(missing))
    print("schema_apply_complete: 완료")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-file", type=Path, default=DEFAULT_SCHEMA_FILE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    load_dotenv()
    apply_schema(args.schema_file, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
