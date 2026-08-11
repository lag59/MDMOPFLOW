from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Engine

from app.core.config import settings


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return cfg


def expected_alembic_heads() -> set[str]:
    script = ScriptDirectory.from_config(_alembic_config())
    return set(script.get_heads())


def current_database_heads(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return set(context.get_current_heads() or [])


def assert_schema_is_current(engine: Engine) -> None:
    expected = expected_alembic_heads()
    current = current_database_heads(engine)

    if not expected:
        raise RuntimeError("Alembic script directory has no heads; migrations are not configured.")
    if not current:
        raise RuntimeError(
            "Database is missing Alembic version state. Run migrations before API startup."
        )
    if expected != current:
        raise RuntimeError(
            "Database schema is out of date. "
            f"Expected heads={sorted(expected)}, current={sorted(current)}. "
            "Run 'alembic upgrade head' before starting the API."
        )
