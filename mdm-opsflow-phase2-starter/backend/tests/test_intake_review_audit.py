from __future__ import annotations

from datetime import datetime, timedelta
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


def test_dead_letter_event_can_be_replayed_with_operator_approval_notes(client: TestClient) -> None:
    user = register_user(client, "event-replay@example.com", "Pass12345!", "Event Replay Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Replay Civil", "Replay Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-replay.txt", b"Ticket: TCK-9001\n", "text/plain")},
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

    invalid_replay = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "Operator override"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert invalid_replay.status_code == 400
    assert invalid_replay.json()["detail"] == "Only dead-lettered events can be replayed"

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
    assert dead_letter_response.json()["status"] == "dead_lettered"

    replay_without_notes = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "   "},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert replay_without_notes.status_code == 400
    assert replay_without_notes.json()["detail"] == "approval_notes is required"

    replay_response = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "Ops manager approved replay after incident review"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert replay_response.status_code == 200
    replayed_event = replay_response.json()

    assert replayed_event["status"] == "pending"
    assert replayed_event["processed_at"] is None
    replayed_payload = json.loads(replayed_event["payload_json"])
    assert replayed_payload["replay_count"] == 1
    assert replayed_payload["replay_approved_by"] == user["user_id"]
    assert replayed_payload["replay_approval_notes"] == "Ops manager approved replay after incident review"
    assert "replay_approved_at" in replayed_payload
    assert "dead_letter_reason" not in replayed_payload

    with TestingSessionLocal() as db:
        replay_audit_log = db.scalars(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .where(AuditLog.resource_type == "integration_event")
            .where(AuditLog.resource_id == target_event["id"])
            .where(AuditLog.action == "replay_dead_letter_intake_event")
        ).first()

    assert replay_audit_log is not None
    assert "Ops manager approved replay after incident review" in replay_audit_log.details
    assert "replay_count=1" in replay_audit_log.details

    pending_after = client.get(
        "/api/intake/events",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert pending_after.status_code == 200
    assert any(event["id"] == target_event["id"] for event in pending_after.json())


def test_replay_history_lists_manual_replay_audit_entries(client: TestClient) -> None:
    user = register_user(client, "event-replay-history@example.com", "Pass12345!", "Replay History Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Replay History Civil", "Replay History Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-replay-history.txt", b"Ticket: TCK-9002\n", "text/plain")},
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
    assert dead_letter_response.json()["status"] == "dead_lettered"

    replay_response = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "Approved for replay in ops review"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert replay_response.status_code == 200

    history_response = client.get(
        "/api/intake/events/replay-history",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert history_response.status_code == 200
    history_entries = history_response.json()
    matching_entries = [entry for entry in history_entries if entry["resource_id"] == target_event["id"]]
    assert len(matching_entries) == 1

    replay_entry = matching_entries[0]
    assert replay_entry["tenant_id"] == tenant_id
    assert replay_entry["action"] == "replay_dead_letter_intake_event"
    assert replay_entry["resource_type"] == "integration_event"
    assert replay_entry["actor_user_id"] == user["user_id"]
    assert "Approved for replay in ops review" in replay_entry["details"]

    filtered_response = client.get(
        "/api/intake/events/replay-history",
        params={"event_id": target_event["id"]},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert filtered_response.status_code == 200
    filtered_entries = filtered_response.json()
    assert len(filtered_entries) == 1
    assert filtered_entries[0]["resource_id"] == target_event["id"]


def test_replay_history_export_supports_csv_json_and_date_validation(client: TestClient) -> None:
    user = register_user(client, "event-replay-export@example.com", "Pass12345!", "Replay Export Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Replay Export Civil", "Replay Export Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-replay-export.txt", b"Ticket: TCK-9003\n", "text/plain")},
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
    assert dead_letter_response.json()["status"] == "dead_lettered"

    replay_response = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "Approved for export replay history test"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert replay_response.status_code == 200

    csv_export = client.get(
        "/api/intake/events/replay-history/export",
        params={"event_id": target_event["id"]},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert csv_export.status_code == 200
    assert "text/csv" in csv_export.headers["content-type"]
    assert "attachment;" in csv_export.headers["content-disposition"]
    assert "intake-replay-history-" in csv_export.headers["content-disposition"]
    assert ".csv\"" in csv_export.headers["content-disposition"]
    csv_body = csv_export.text
    assert "resource_id" in csv_body
    assert target_event["id"] in csv_body
    assert "Approved for export replay history test" in csv_body

    json_export = client.get(
        "/api/intake/events/replay-history/export",
        params={"output": "json", "event_id": target_event["id"]},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert json_export.status_code == 200
    assert "attachment;" in json_export.headers["content-disposition"]
    assert "intake-replay-history-" in json_export.headers["content-disposition"]
    assert ".json\"" in json_export.headers["content-disposition"]
    payload = json_export.json()
    assert len(payload) == 1
    assert payload[0]["resource_id"] == target_event["id"]

    start_created_at = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end_created_at = datetime.utcnow().isoformat()
    invalid_range = client.get(
        "/api/intake/events/replay-history/export",
        params={
            "start_created_at": start_created_at,
            "end_created_at": end_created_at,
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert invalid_range.status_code == 400
    assert invalid_range.json()["detail"] == "start_created_at must be <= end_created_at"


def test_replay_history_supports_cursor_pagination_for_list_and_export(client: TestClient) -> None:
    user = register_user(client, "event-replay-cursor@example.com", "Pass12345!", "Replay Cursor Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Replay Cursor Civil", "Replay Cursor Project")
    tenant_id = onboarding["tenant_id"]

    def create_replay_entry(ticket_number: str, approval_notes: str) -> str:
        upload_response = client.post(
            "/api/intake/upload",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
            files={"file": (f"ticket-{ticket_number}.txt", f"Ticket: {ticket_number}\n".encode(), "text/plain")},
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
        assert dead_letter_response.json()["status"] == "dead_lettered"

        replay_response = client.post(
            f"/api/intake/events/{target_event['id']}/replay-dead-letter",
            json={"approval_notes": approval_notes},
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert replay_response.status_code == 200
        return target_event["id"]

    event_id_1 = create_replay_entry("TCK-9101", "First cursor replay")
    event_id_2 = create_replay_entry("TCK-9102", "Second cursor replay")

    list_page_1 = client.get(
        "/api/intake/events/replay-history",
        params={"limit": 1},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert list_page_1.status_code == 200
    list_page_1_items = list_page_1.json()
    assert len(list_page_1_items) == 1
    next_cursor = list_page_1.headers.get("x-next-cursor-created-at")
    assert next_cursor is not None

    list_page_2 = client.get(
        "/api/intake/events/replay-history",
        params={"limit": 1, "cursor_created_at": next_cursor},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert list_page_2.status_code == 200
    list_page_2_items = list_page_2.json()
    assert len(list_page_2_items) == 1
    assert list_page_2_items[0]["id"] != list_page_1_items[0]["id"]

    listed_ids = {list_page_1_items[0]["resource_id"], list_page_2_items[0]["resource_id"]}
    assert event_id_1 in listed_ids
    assert event_id_2 in listed_ids

    export_page_1 = client.get(
        "/api/intake/events/replay-history/export",
        params={"output": "json", "limit": 1},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert export_page_1.status_code == 200
    export_page_1_items = export_page_1.json()
    assert len(export_page_1_items) == 1
    export_cursor = export_page_1.headers.get("x-next-cursor-created-at")
    assert export_cursor is not None

    export_page_2 = client.get(
        "/api/intake/events/replay-history/export",
        params={"output": "json", "limit": 1, "cursor_created_at": export_cursor},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert export_page_2.status_code == 200
    export_page_2_items = export_page_2.json()
    assert len(export_page_2_items) == 1
    assert export_page_2_items[0]["id"] != export_page_1_items[0]["id"]


def test_replay_history_export_token_supports_signed_one_time_download(client: TestClient) -> None:
    user = register_user(client, "event-replay-token@example.com", "Pass12345!", "Replay Token Owner")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Replay Token Civil", "Replay Token Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-replay-token.txt", b"Ticket: TCK-9200\n", "text/plain")},
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
    assert dead_letter_response.json()["status"] == "dead_lettered"

    replay_response = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "Approved for signed export token test"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert replay_response.status_code == 200

    token_response = client.post(
        "/api/intake/events/replay-history/export-token",
        params={"tenant_id": tenant_id, "event_id": target_event["id"], "output": "json"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert token_response.status_code == 200

    token_payload = token_response.json()
    assert token_payload["token"]
    assert token_payload["download_url"].startswith("/api/intake/events/replay-history/export/download?token=")
    assert token_payload["expires_at"]

    first_download = client.get(token_payload["download_url"])
    assert first_download.status_code == 200
    first_download_payload = first_download.json()
    assert len(first_download_payload) == 1
    assert first_download_payload[0]["resource_id"] == target_event["id"]
    assert "attachment;" in first_download.headers["content-disposition"]
    assert "intake-replay-history-" in first_download.headers["content-disposition"]
    assert ".json\"" in first_download.headers["content-disposition"]

    second_download = client.get(token_payload["download_url"])
    assert second_download.status_code == 410
    assert second_download.json()["detail"] == "Export token has already been used"

    invalid_download = client.get(
        "/api/intake/events/replay-history/export/download",
        params={"token": "invalid-token"},
    )
    assert invalid_download.status_code == 401
    assert invalid_download.json()["detail"] == "Invalid export token"


def test_replay_history_export_token_can_be_revoked_before_download(client: TestClient) -> None:
    user = register_user(client, "event-replay-token-revoke@example.com", "Pass12345!", "Replay Token Revoker")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Replay Token Revoke Civil", "Replay Token Revoke Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-replay-token-revoke.txt", b"Ticket: TCK-9300\n", "text/plain")},
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
    assert dead_letter_response.json()["status"] == "dead_lettered"

    replay_response = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "Approved for signed export token revoke test"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert replay_response.status_code == 200

    token_response = client.post(
        "/api/intake/events/replay-history/export-token",
        params={"tenant_id": tenant_id, "event_id": target_event["id"], "output": "json"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()

    revoke_response = client.post(
        "/api/intake/events/replay-history/export-token/revoke",
        json={"token": token_payload["token"]},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert revoke_response.status_code == 200
    revoke_payload = revoke_response.json()
    assert revoke_payload["token_id"]
    assert revoke_payload["revoked"] is True
    assert revoke_payload["revoked_at"]

    revoked_download = client.get(token_payload["download_url"])
    assert revoked_download.status_code == 410
    assert revoked_download.json()["detail"] == "Export token has been revoked"

    repeat_revoke = client.post(
        "/api/intake/events/replay-history/export-token/revoke",
        json={"token": token_payload["token"]},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert repeat_revoke.status_code == 409
    assert repeat_revoke.json()["detail"] == "Export token has already been revoked"


def test_replay_export_token_audit_history_supports_action_actor_and_cursor_filters(client: TestClient) -> None:
    user = register_user(client, "event-replay-token-audit@example.com", "Pass12345!", "Replay Token Auditor")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Replay Token Audit Civil", "Replay Token Audit Project")
    tenant_id = onboarding["tenant_id"]

    upload_response = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-replay-token-audit.txt", b"Ticket: TCK-9400\n", "text/plain")},
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
    assert dead_letter_response.json()["status"] == "dead_lettered"

    replay_response = client.post(
        f"/api/intake/events/{target_event['id']}/replay-dead-letter",
        json={"approval_notes": "Approved for signed export token audit test"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert replay_response.status_code == 200

    consume_token_response = client.post(
        "/api/intake/events/replay-history/export-token",
        params={"tenant_id": tenant_id, "event_id": target_event["id"], "output": "json"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert consume_token_response.status_code == 200
    consume_token_payload = consume_token_response.json()

    consume_download = client.get(consume_token_payload["download_url"])
    assert consume_download.status_code == 200

    revoke_token_response = client.post(
        "/api/intake/events/replay-history/export-token",
        params={"tenant_id": tenant_id, "event_id": target_event["id"], "output": "json"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert revoke_token_response.status_code == 200
    revoke_token_payload = revoke_token_response.json()

    revoke_response = client.post(
        "/api/intake/events/replay-history/export-token/revoke",
        json={"token": revoke_token_payload["token"]},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert revoke_response.status_code == 200

    history_response = client.get(
        "/api/intake/events/replay-history/export-token-history",
        params={"tenant_id": tenant_id},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert history_response.status_code == 200
    history_entries = history_response.json()
    actions = [entry["action"] for entry in history_entries]
    assert actions.count("issue_replay_history_export_token") == 2
    assert actions.count("consume_replay_history_export_token") == 1
    assert actions.count("revoke_replay_history_export_token") == 1

    revoke_only_response = client.get(
        "/api/intake/events/replay-history/export-token-history",
        params={
            "tenant_id": tenant_id,
            "action": "revoke_replay_history_export_token",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert revoke_only_response.status_code == 200
    revoke_only_entries = revoke_only_response.json()
    assert len(revoke_only_entries) == 1
    assert revoke_only_entries[0]["action"] == "revoke_replay_history_export_token"

    actor_filter_response = client.get(
        "/api/intake/events/replay-history/export-token-history",
        params={
            "tenant_id": tenant_id,
            "actor_user_id": user["user_id"],
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert actor_filter_response.status_code == 200
    actor_entries = actor_filter_response.json()
    assert len(actor_entries) >= 4
    assert all(entry["actor_user_id"] == user["user_id"] for entry in actor_entries)

    paged_history_response = client.get(
        "/api/intake/events/replay-history/export-token-history",
        params={"tenant_id": tenant_id, "limit": 2},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert paged_history_response.status_code == 200
    paged_entries = paged_history_response.json()
    assert len(paged_entries) == 2
    next_cursor = paged_history_response.headers.get("x-next-cursor-created-at")
    assert next_cursor is not None

    paged_history_next_response = client.get(
        "/api/intake/events/replay-history/export-token-history",
        params={"tenant_id": tenant_id, "limit": 2, "cursor_created_at": next_cursor},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert paged_history_next_response.status_code == 200
    paged_next_entries = paged_history_next_response.json()
    assert len(paged_next_entries) >= 1
    assert paged_next_entries[0]["id"] != paged_entries[0]["id"]
