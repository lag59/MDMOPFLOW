from collections.abc import Generator
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.observability import get_request_id

from app.core.config import settings


class Base(DeclarativeBase):
    pass


logger = logging.getLogger(__name__)


database_url = make_url(settings.DATABASE_URL)
engine_kwargs = {"future": True, "pool_pre_ping": True}

if database_url.drivername.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update(
        {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }
    )

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    _ = cursor, parameters, executemany
    context._query_start_time = time.perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    _ = conn, cursor, parameters, executemany
    start_time = getattr(context, "_query_start_time", None)
    if start_time is None:
        return
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    statement_type = statement.strip().split(" ", 1)[0].upper() if statement else "UNKNOWN"
    logger.info(
        "db_query_completed",
        extra={
            "request_id": get_request_id(),
            "statement_type": statement_type,
            "latency_ms": elapsed_ms,
        },
    )


@event.listens_for(engine, "handle_error")
def _handle_db_error(context):
    statement = context.statement or ""
    statement_type = statement.strip().split(" ", 1)[0].upper() if statement else "UNKNOWN"
    logger.error(
        "db_query_failed",
        extra={
            "request_id": get_request_id(),
            "statement_type": statement_type,
            "db_error_class": context.original_exception.__class__.__name__,
            "error_classification": "database_error",
        },
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
