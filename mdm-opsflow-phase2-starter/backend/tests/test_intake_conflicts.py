from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from app.models import AuditLog, IntegrationEvent

from .helpers import complete_onboarding, register_user


TEST_DB_URL = "sqlite:///./test_opsflow.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def test_conflict_suggestion_recommends_addendum_over_bid_schedule(client: TestClient) -> None:
    user = register_user(client, "conflict-user@example.com", "Pass12345!", "Conflict User")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Conflict Civil", "Conflict Project")
    tenant_id = onboarding["tenant_id"]

    bid_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "bid-schedule.txt",
                b"Bid Schedule\nExport Excavation: 13,300 CY\n",
                "text/plain",
            )
        },
    )
    assert bid_upload.status_code == 201, bid_upload.text

    addendum_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "addendum-2.txt",
                b"Addendum No. 2\nExport quantity revised to 15,100 CY\n",
                "text/plain",
            )
        },
    )
    assert addendum_upload.status_code == 201, addendum_upload.text

    response = client.post(
        "/api/intake/conflicts/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [bid_upload.json()["id"], addendum_upload.json()["id"]]},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["items"]) == 1

    suggestion = payload["items"][0]
    assert suggestion["field_name"] == "export_quantity"
    assert suggestion["recommended"]["value"] == 15100.0
    assert suggestion["recommended"]["document_type"] == "addendum"


def test_conflict_resolution_is_audited(client: TestClient) -> None:
    user = register_user(client, "conflict-review@example.com", "Pass12345!", "Conflict Reviewer")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Conflict Review Civil", "Conflict Review Project")
    tenant_id = onboarding["tenant_id"]

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "addendum-3.txt",
                b"Addendum No. 3\nExport quantity revised to 16,200 CY\n",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    item_id = upload.json()["id"]

    resolve = client.post(
        "/api/intake/conflicts/resolve",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={
            "field_name": "export_quantity",
            "selected_item_id": item_id,
            "selected_value": 16200,
            "rationale": "Addendum supersedes bid schedule.",
        },
    )
    assert resolve.status_code == 204, resolve.text

    with TestingSessionLocal() as db:
        audit = db.scalars(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .where(AuditLog.resource_type == "intake_item")
            .where(AuditLog.resource_id == item_id)
            .where(AuditLog.action == "resolve_intake_conflict")
        ).first()
        event = db.scalars(
            select(IntegrationEvent)
            .where(IntegrationEvent.tenant_id == tenant_id)
            .where(IntegrationEvent.resource_type == "intake_item")
            .where(IntegrationEvent.resource_id == item_id)
            .where(IntegrationEvent.event_type == "intake_conflict_resolved")
        ).first()

    assert audit is not None
    assert "field=export_quantity" in audit.details
    assert "selected_value=16200.0" in audit.details

    assert event is not None
