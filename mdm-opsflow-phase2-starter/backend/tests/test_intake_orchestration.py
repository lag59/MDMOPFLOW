from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import IngestionBatch, IngestionBatchStatus

from .helpers import complete_onboarding, register_user


TEST_DB_URL = "sqlite:///./test_opsflow.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def test_upload_creates_batch_and_ticket_from_extracted_entities(client: TestClient) -> None:
    user = register_user(client, "intake-orch@example.com", "Pass12345!", "Intake Orchestrator")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Orchestration Civil", "Orchestration First")
    tenant_id = onboarding["tenant_id"]

    payload = (
        b"Ticket: TCK-9001\n"
        b"Driver: Jamie Stone\n"
        b"Truck: Unit 42\n"
        b"Material: Rock\n"
    )

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-9001.txt", payload, "text/plain")},
    )
    assert upload_response.status_code == 201
    uploaded_item = upload_response.json()

    tickets_response = client.get(
        "/api/tickets",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert tickets_response.status_code == 200
    tickets = tickets_response.json()
    assert len(tickets) == 1
    assert tickets[0]["ticket_number"] == "TCK-9001"
    assert tickets[0]["driver"] == "Jamie Stone"

    with TestingSessionLocal() as db:
        batch = db.scalars(
            select(IngestionBatch)
            .where(IngestionBatch.id == uploaded_item["batch_id"])
            .where(IngestionBatch.tenant_id == tenant_id)
        ).first()

    assert batch is not None
    assert batch.status == IngestionBatchStatus.COMPLETED
    assert batch.total_documents == 1
    assert batch.created_documents == 1
    assert batch.matched_documents == 1

    summary = json.loads(batch.summary_json)
    assert uploaded_item["id"] in summary["created_item_ids"]
    assert len(summary["created_ticket_ids"]) == 1
