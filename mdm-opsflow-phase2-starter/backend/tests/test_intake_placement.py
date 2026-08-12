from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from app.models import AuditLog

from .helpers import complete_onboarding, register_user


TEST_DB_URL = "sqlite:///./test_opsflow.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def test_intake_placement_suggestions_are_returned_and_audited(client: TestClient) -> None:
    user = register_user(client, "placement-user@example.com", "Pass12345!", "Placement User")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Placement Civil", "Placement Project")
    tenant_id = onboarding["tenant_id"]

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "ticket-placement.txt",
                b"Ticket: TCK-9001\nDriver: Sam\nMaterial: Base Rock\n",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    item_id = upload.json()["id"]

    suggest = client.post(
        "/api/intake/placement/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [item_id]},
    )
    assert suggest.status_code == 200, suggest.text
    payload = suggest.json()
    assert len(payload["items"]) == 1
    suggestion = payload["items"][0]
    assert suggestion["item_id"] == item_id
    assert suggestion["destination_key"] == "tickets"
    assert suggestion["destination_href"] == "/tickets"

    with TestingSessionLocal() as db:
        log = db.scalars(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .where(AuditLog.resource_type == "intake_item")
            .where(AuditLog.resource_id == item_id)
            .where(AuditLog.action == "ai_suggest_intake_placement")
        ).first()

    assert log is not None
    assert "destination=tickets" in log.details
