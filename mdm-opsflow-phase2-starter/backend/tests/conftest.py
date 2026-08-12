import os
import warnings
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test_opsflow.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SUPER_ADMIN_EMAIL"] = "founder@mdmopsflow.com"
os.environ["SUPER_ADMIN_PASSWORD"] = "ChangeMe123!"
os.environ["MIGRATION_ENFORCE_SCHEMA_ON_STARTUP"] = "false"
os.environ["OPENAI_API_KEY"] = ""

from app.db import Base, get_db
from app.main import app


TEST_DB_URL = "sqlite:///./test_opsflow.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    warnings.filterwarnings(
        "ignore",
        message=r"Can't sort tables for DROP; an unresolvable foreign key dependency exists between tables: document_extractions, tickets;.*",
        category=SAWarning,
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _disable_external_ai_calls(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Force deterministic local summaries in tests and avoid live AI/network calls."""

    def _local_summary(raw_text: str, *, entities: dict[str, str], original_filename: str = "") -> str:
        del raw_text, original_filename
        summary_parts: list[str] = []
        if entities.get("ticket_number"):
            summary_parts.append(f"Ticket {entities['ticket_number']}")
        if entities.get("driver"):
            summary_parts.append(f"Driver {entities['driver']}")
        if entities.get("truck"):
            summary_parts.append(f"Truck {entities['truck']}")
        if entities.get("material"):
            summary_parts.append(f"Material {entities['material']}")
        return "; ".join(summary_parts)

    monkeypatch.setattr("app.services.ticket_extractor.summarize_ticket_preview", _local_summary, raising=False)
    monkeypatch.setattr("app.services.llm_client.summarize_ticket_preview", _local_summary, raising=False)
    yield
