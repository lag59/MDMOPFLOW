from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import AuditLog
from tests.helpers import complete_onboarding, register_user


def test_document_intake_config_requires_tenant_scope_and_returns_policy(client: TestClient) -> None:
    user = register_user(client, "document-intake-config@example.com", "Pass12345!", "Document Intake Config")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Document Intake Config Civil", "Config Project")
    tenant_id = onboarding["tenant_id"]

    response = client.get(
        "/api/document-intake/config",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["auto_route_min_confidence"] == 0.72
    assert payload["auto_post_financial_or_ticket_min_confidence"] == 0.9
    assert payload["never_silent_overwrite"] is True
    assert payload["require_tenant_scope"] is True
    assert payload["create_audit_event"] is True
    assert payload["routes"]["haul_ticket"] == "Tickets > Hauling"
    assert payload["routes"]["unknown"] == "Review Queue > Unclassified"


def test_document_intake_config_requires_explicit_tenant_for_super_admin(client: TestClient) -> None:
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    missing_scope = client.get("/api/document-intake/config", headers={"Authorization": f"Bearer {admin_token}"})

    assert missing_scope.status_code == 400


def test_document_intake_upload_returns_strict_route_json_and_audits(client: TestClient) -> None:
    user = register_user(client, "document-intake-upload@example.com", "Pass12345!", "Document Intake Upload")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Document Intake Upload Civil", "Upload Project")
    tenant_id = onboarding["tenant_id"]

    response = client.post(
        "/api/document-intake",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "haul-ticket.txt",
                (
                    b"HAUL TICKET - TEST OCR DOCUMENT\n"
                    b"Carolina Haul Services\n"
                    b"Ticket No. CH-004821\n"
                    b"Date 08/11/2026\n"
                    b"Project N. Ridge Commerce Pk Ph 2\n"
                    b"Truck T-17\n"
                    b"Driver M. SAMPLE\n"
                    b"Material EXPORT SOIL\n"
                    b"Load 18.6 tons\n"
                    b"Origin NRCP PH2\n"
                    b"Destination DURHAM FILL SITE B\n"
                    b"Time In 10:42\n"
                    b"Time Out 11:06"
                ),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload == {
        "document_type": "haul_ticket",
        "classification_confidence": 0.99,
        "recommended_route": "Tickets > Hauling",
        "project": {"name": "North Ridge Commerce Park - Phase 2", "number": None, "match_confidence": 0.0},
        "vendor": {"name": "Carolina Haul Services", "document_number": "CH-004821"},
        "extracted_fields": {
            "ticket_number": "CH-004821",
            "date": "08/11/2026",
            "project": "North Ridge Commerce Park - Phase 2",
            "truck": "T-17",
            "driver": "M. SAMPLE",
            "material": "EXPORT SOIL",
            "origin": "NRCP PH2",
            "destination": "DURHAM FILL SITE B",
            "time_in": "10:42",
            "time_out": "11:06",
            "load_value": 18.6,
            "load_unit": "TON",
        },
        "uncertain_fields": [],
        "conflicts": [],
        "requires_human_review": False,
        "reason_for_review": None,
    }

    with SessionLocal() as db:
        audit = db.query(AuditLog).filter(AuditLog.action == "document_intake_route_preview").one()
        assert audit.tenant_id == tenant_id
        assert audit.resource_id == "haul-ticket.txt"
        assert "document_type=haul_ticket" in audit.details