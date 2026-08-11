from __future__ import annotations

from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings


def _validate_database_url() -> str:
    try:
        parsed = make_url(settings.DATABASE_URL)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Invalid DATABASE_URL: {exc}") from exc

    if not parsed.drivername:
        raise RuntimeError("Invalid DATABASE_URL: missing SQLAlchemy driver name")

    return settings.DATABASE_URL


def _check_database_connectivity(database_url: str) -> None:
    engine = create_engine(database_url, future=True, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Database connectivity check failed: {exc}") from exc
    finally:
        engine.dispose()


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _verify_single_head(cfg: Config) -> set[str]:
    heads = set(ScriptDirectory.from_config(cfg).get_heads())
    if not heads:
        raise RuntimeError("No Alembic head revisions found.")
    if len(heads) > 1:
        raise RuntimeError(f"Multiple Alembic heads found: {sorted(heads)}")
    return heads


def _verify_migration_outcome(database_url: str, expected_heads: set[str]) -> None:
    engine = create_engine(database_url, future=True, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            current_heads = set(MigrationContext.configure(conn).get_current_heads() or [])
    finally:
        engine.dispose()

    if current_heads != expected_heads:
        raise RuntimeError(
            "Migration completed but schema head mismatch detected. "
            f"Expected={sorted(expected_heads)}, current={sorted(current_heads)}"
        )


def main() -> int:
    try:
        database_url = _validate_database_url()
        _check_database_connectivity(database_url)
        cfg = _alembic_config(database_url)
        expected_heads = _verify_single_head(cfg)

        # Deterministic migration execution: a single upgrade path to head.
        command.upgrade(cfg, "head")
        _verify_migration_outcome(database_url, expected_heads)
    except Exception as exc:
        print(f"[migration-safety] migration failed: {exc}", file=sys.stderr)
        return 1

    print("[migration-safety] migrations applied successfully and schema is at head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
