from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditLog, IntegrationEvent

from .helpers import complete_onboarding, register_user


TEST_DB_URL = "sqlite:///./test_opsflow.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def test_approve_and_reject_create_audit_entries(client: TestClient) -> None:
    user = register_user(client, "intake-audit@example.com", "Pass12345!", "Intake Auditor")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Audit Civil", "Audit Project")
    tenant_id = onboarding["tenant_id"]

    first_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-approve.txt", b"Ticket: TCK-3001\n", "text/plain")},
    )
    assert first_upload.status_code == 201
    first_item = first_upload.json()

    approve_response = client.post(
        f"/api/intake/items/{first_item['id']}/approve",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    second_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-reject.txt", b"Ticket: TCK-3002\n", "text/plain")},
    )
    assert second_upload.status_code == 201
    second_item = second_upload.json()

    reject_response = client.post(
        f"/api/intake/items/{second_item['id']}/reject",
        params={"reason": "Missing load signature"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    with TestingSessionLocal() as db:
        approve_log = db.scalars(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .where(AuditLog.resource_type == "intake_item")
            .where(AuditLog.resource_id == first_item["id"])
            .where(AuditLog.action == "approve_intake_item")
        ).first()
        reject_log = db.scalars(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .where(AuditLog.resource_type == "intake_item")
            .where(AuditLog.resource_id == second_item["id"])
            .where(AuditLog.action == "reject_intake_item")
        ).first()
        upload_event = db.scalars(
            select(IntegrationEvent)
            .where(IntegrationEvent.tenant_id == tenant_id)
            .where(IntegrationEvent.resource_type == "intake_item")
            .where(IntegrationEvent.resource_id == first_item["id"])
            .where(IntegrationEvent.event_type == "intake_item_uploaded")
        ).first()
        approve_event = db.scalars(
            select(IntegrationEvent)
            .where(IntegrationEvent.tenant_id == tenant_id)
            .where(IntegrationEvent.resource_type == "intake_item")
            .where(IntegrationEvent.resource_id == first_item["id"])
            .where(IntegrationEvent.event_type == "intake_item_approved")
        ).first()
        reject_event = db.scalars(
            select(IntegrationEvent)
            .where(IntegrationEvent.tenant_id == tenant_id)
            .where(IntegrationEvent.resource_type == "intake_item")
            .where(IntegrationEvent.resource_id == second_item["id"])
            .where(IntegrationEvent.event_type == "intake_item_rejected")
        ).first()

    assert approve_log is not None
    assert "approved" in approve_log.details

    assert reject_log is not None
    assert "Missing load signature" in reject_log.details

    assert upload_event is not None
    upload_payload = json.loads(upload_event.payload_json)
    assert upload_payload["batch_id"] == first_item["batch_id"]
    assert upload_payload["status"] == first_item["status"]

    assert approve_event is not None
    approve_payload = json.loads(approve_event.payload_json)
    assert approve_payload["status"] == "approved"
    assert approve_payload["needs_review"] is False

    assert reject_event is not None
    reject_payload = json.loads(reject_event.payload_json)
    assert reject_payload["status"] == "rejected"
    assert reject_payload["review_reason"] == "Missing load signature"


def test_duplicate_resolution_clears_review_and_logs_audit(client: TestClient) -> None:
    user = register_user(client, "resolve-dup@example.com", "Pass12345!", "Duplicate Resolver")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Resolve Civil", "Resolve Project")
    tenant_id = onboarding["tenant_id"]

    duplicate_payload = (
        b"Ticket: TCK-4010\n"
        b"Driver: Avery Nash\n"
        b"Truck: Unit 20\n"
        b"Material: Base Rock\n"
    )

    first_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-4010.txt", duplicate_payload, "text/plain")},
    )
    assert first_upload.status_code == 201
    first_item = first_upload.json()

    second_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-4010-copy.txt", duplicate_payload, "text/plain")},
    )
    assert second_upload.status_code == 201
    second_item = second_upload.json()
    assert second_item["needs_review"] is True

    resolve_response = client.post(
        f"/api/intake/items/{second_item['id']}/resolve-duplicate",
        json={"conflict_notes": "Confirmed duplicate after reviewer comparison."},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert resolve_response.status_code == 200

    resolved = resolve_response.json()
    assert resolved["status"] == "approved"
    assert resolved["needs_review"] is False
    assert resolved["reviewed_by"] == user["user_id"]
    assert resolved["duplicate_of_item_id"] == first_item["id"]

    with TestingSessionLocal() as db:
        resolution_log = db.scalars(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .where(AuditLog.resource_type == "intake_item")
            .where(AuditLog.resource_id == second_item["id"])
            .where(AuditLog.action == "resolve_intake_duplicate")
        ).first()
        duplicate_upload_event = db.scalars(
            select(IntegrationEvent)
            .where(IntegrationEvent.tenant_id == tenant_id)
            .where(IntegrationEvent.resource_type == "intake_item")
            .where(IntegrationEvent.resource_id == second_item["id"])
            .where(IntegrationEvent.event_type == "intake_item_uploaded")
        ).first()
        resolve_event = db.scalars(
            select(IntegrationEvent)
            .where(IntegrationEvent.tenant_id == tenant_id)
            .where(IntegrationEvent.resource_type == "intake_item")
            .where(IntegrationEvent.resource_id == second_item["id"])
            .where(IntegrationEvent.event_type == "intake_item_duplicate_resolved")
        ).first()

    assert resolution_log is not None
    assert first_item["id"] in resolution_log.details
    assert "Confirmed duplicate" in resolution_log.details

    assert duplicate_upload_event is not None
    duplicate_upload_payload = json.loads(duplicate_upload_event.payload_json)
    assert duplicate_upload_payload["status"] == second_item["status"]
    assert duplicate_upload_payload["needs_review"] is True
    assert duplicate_upload_payload["duplicate_of_item_id"] == first_item["id"]

    assert resolve_event is not None
    resolve_payload = json.loads(resolve_event.payload_json)
    assert resolve_payload["status"] == "approved"
    assert resolve_payload["needs_review"] is False
    assert resolve_payload["duplicate_of_item_id"] == first_item["id"]


def test_intake_integration_event_queue_can_be_processed(client: TestClient) -> None:
    user = register_user(client, "event-queue@example.com", "Pass12345!", "Event Queue Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Queue Civil", "Queue Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-queue.txt", b"Ticket: TCK-5090\n", "text/plain")},
    )
    assert upload_response.status_code == 201
    item = upload_response.json()

    pending_response = client.get(
        "/api/intake/events",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert pending_response.status_code == 200
    pending_events = pending_response.json()
    assert len(pending_events) >= 1

    matching_pending = [event for event in pending_events if event["resource_id"] == item["id"]]
    assert len(matching_pending) == 1
    pending_event = matching_pending[0]
    assert pending_event["event_type"] == "intake_item_uploaded"
    assert pending_event["status"] == "pending"

    process_response = client.post(
        f"/api/intake/events/{pending_event['id']}/mark-processed",
        json={"status": "processed", "processing_notes": "Exported to accounting bridge"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert process_response.status_code == 200
    processed_event = process_response.json()

    assert processed_event["status"] == "processed"
    assert processed_event["processed_at"] is not None
    processed_payload = json.loads(processed_event["payload_json"])
    assert processed_payload["processed_by"] == user["user_id"]
    assert processed_payload["processing_notes"] == "Exported to accounting bridge"

    pending_after_response = client.get(
        "/api/intake/events",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert pending_after_response.status_code == 200
    pending_after = pending_after_response.json()
    assert all(event["id"] != pending_event["id"] for event in pending_after)

    processed_list_response = client.get(
        "/api/intake/events",
        params={"status": "processed"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert processed_list_response.status_code == 200
    processed_list = processed_list_response.json()
    assert any(event["id"] == pending_event["id"] for event in processed_list)


def test_failed_event_requires_reason_and_can_be_retried(client: TestClient) -> None:
    user = register_user(client, "event-retry@example.com", "Pass12345!", "Event Retry Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Retry Civil", "Retry Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-retry.txt", b"Ticket: TCK-7001\n", "text/plain")},
    )
    assert upload_response.status_code == 201
    item = upload_response.json()

    pending_response = client.get(
        "/api/intake/events",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert pending_response.status_code == 200
    pending_events = pending_response.json()
    target_event = [event for event in pending_events if event["resource_id"] == item["id"]][0]

    fail_without_reason = client.post(
        f"/api/intake/events/{target_event['id']}/mark-processed",
        json={"status": "failed", "processing_notes": "Bridge returned 500", "failure_reason": ""},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert fail_without_reason.status_code == 400
    assert fail_without_reason.json()["detail"] == "failure_reason is required when status=failed"

    fail_with_reason = client.post(
        f"/api/intake/events/{target_event['id']}/mark-processed",
        json={
            "status": "failed",
            "processing_notes": "Bridge returned 500",
            "failure_reason": "Remote accounting API timeout",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert fail_with_reason.status_code == 200
    failed_event = fail_with_reason.json()
    assert failed_event["status"] == "failed"
    assert failed_event["processed_at"] is not None
    failed_payload = json.loads(failed_event["payload_json"])
    assert failed_payload["failure_reason"] == "Remote accounting API timeout"

    retry_response = client.post(
        f"/api/intake/events/{target_event['id']}/retry",
        json={"retry_notes": "Retry after API health recovered"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert retry_response.status_code == 200
    retried_event = retry_response.json()

    assert retried_event["status"] == "pending"
    assert retried_event["processed_at"] is None
    retried_payload = json.loads(retried_event["payload_json"])
    assert retried_payload["retry_count"] == 1
    assert retried_payload["last_retry_by"] == user["user_id"]
    assert retried_payload["last_retry_notes"] == "Retry after API health recovered"
    assert "failure_reason" not in retried_payload


def test_event_moves_to_dead_letter_after_exceeding_max_retries(client: TestClient) -> None:
    user = register_user(client, "event-deadletter@example.com", "Pass12345!", "Event Deadletter Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Deadletter Civil", "Deadletter Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-deadletter.txt", b"Ticket: TCK-8001\n", "text/plain")},
    )
    assert upload_response.status_code == 201
    item = upload_response.json()

    pending_response = client.get(
        "/api/intake/events",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert pending_response.status_code == 200
    target_event = [event for event in pending_response.json() if event["resource_id"] == item["id"]][0]

    for attempt in range(1, 4):
        fail_response = client.post(
            f"/api/intake/events/{target_event['id']}/mark-processed",
            json={
                "status": "failed",
                "processing_notes": f"Attempt {attempt} failed",
                "failure_reason": f"Transient failure {attempt}",
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert fail_response.status_code == 200

        retry_response = client.post(
            f"/api/intake/events/{target_event['id']}/retry",
            json={"retry_notes": f"Retry attempt {attempt}"},
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert retry_response.status_code == 200
        retried_event = retry_response.json()
        assert retried_event["status"] == "pending"
        assert retried_event["processed_at"] is None

    final_fail_response = client.post(
        f"/api/intake/events/{target_event['id']}/mark-processed",
        json={
            "status": "failed",
            "processing_notes": "Attempt 4 failed",
            "failure_reason": "Persistent downstream outage",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert final_fail_response.status_code == 200

    dead_letter_response = client.post(
        f"/api/intake/events/{target_event['id']}/retry",
        json={"retry_notes": "Retry attempt 4"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert dead_letter_response.status_code == 200
    dead_letter_event = dead_letter_response.json()

    assert dead_letter_event["status"] == "dead_lettered"
    assert dead_letter_event["processed_at"] is not None
    dead_letter_payload = json.loads(dead_letter_event["payload_json"])
    assert dead_letter_payload["retry_count"] == 4
    assert dead_letter_payload["dead_lettered_by"] == user["user_id"]
    assert dead_letter_payload["dead_letter_reason"] == "Exceeded max retries (3)"
    assert "dead_lettered_at" in dead_letter_payload

    pending_after = client.get(
        "/api/intake/events",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert pending_after.status_code == 200
    assert all(event["id"] != target_event["id"] for event in pending_after.json())

    dead_letter_list = client.get(
        "/api/intake/events",
        params={"status": "dead_lettered"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert dead_letter_list.status_code == 200
    assert any(event["id"] == target_event["id"] for event in dead_letter_list.json())
