from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

from app.core.config import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Controlled audit-log retention runner")
    parser.add_argument("--days", type=int, default=365, help="Retain this many days of audit records")
    parser.add_argument("--apply", action="store_true", help="Execute deletion (default is dry-run)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(args.days, 1))

    engine = create_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)
    with engine.begin() as conn:
        count_stmt = text("SELECT COUNT(*) FROM audit_logs WHERE occurred_at < :cutoff")
        eligible = conn.execute(count_stmt, {"cutoff": cutoff}).scalar_one()

        if not args.apply:
            print(f"[audit-retention] dry-run eligible_rows={eligible} cutoff={cutoff.isoformat()}")
            return 0

        conn.execute(text("SET LOCAL app.audit_retention_mode = 'on'"))
        delete_stmt = text("DELETE FROM audit_logs WHERE occurred_at < :cutoff")
        result = conn.execute(delete_stmt, {"cutoff": cutoff})
        print(
            "[audit-retention] applied "
            f"deleted_rows={result.rowcount or 0} cutoff={cutoff.isoformat()}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
