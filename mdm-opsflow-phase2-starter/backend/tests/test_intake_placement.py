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


def test_low_confidence_ticket_like_upload_stays_in_extraction_queue(client: TestClient) -> None:
    user = register_user(client, "placement-review@example.com", "Pass12345!", "Placement Reviewer")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Placement Review Civil", "Placement Review Project")
    tenant_id = onboarding["tenant_id"]

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "ticket-number-only.txt",
                b"Ticket: TCK-1001\n",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    item_id = upload.json()["id"]

    suggestions = client.post(
        "/api/intake/placement/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [item_id]},
    )
    assert suggestions.status_code == 200, suggestions.text
    payload = suggestions.json()
    assert len(payload["items"]) == 1
    suggestion = payload["items"][0]
    assert suggestion["destination_key"] == "extraction_queue"
    assert suggestion["signal_source"] == "review_gate"

    tickets = client.get(
        "/api/tickets",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert tickets.status_code == 200, tickets.text
    assert tickets.json() == []


def test_bid_document_with_ticket_like_fields_routes_to_estimator_and_skips_ticket_creation(client: TestClient) -> None:
    user = register_user(client, "placement-bid@example.com", "Pass12345!", "Placement Bid User")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Placement Bid Civil", "Placement Bid Project")
    tenant_id = onboarding["tenant_id"]

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "bid-proposal.txt",
                (
                    b"Bid Proposal\n"
                    b"Scope of Work: Site prep and base rock placement\n"
                    b"Job Number# 16065\n"
                    b"Quantity Takeoff attached\n"
                ),
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    item_id = upload.json()["id"]

    suggestions = client.post(
        "/api/intake/placement/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [item_id]},
    )
    assert suggestions.status_code == 200, suggestions.text
    payload = suggestions.json()
    assert len(payload["items"]) == 1
    suggestion = payload["items"][0]
    assert suggestion["destination_key"] == "estimator"
    assert suggestion["destination_href"] == "/estimator"

    tickets = client.get(
        "/api/tickets",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert tickets.status_code == 200, tickets.text
    assert tickets.json() == []


def test_hauling_quote_routes_to_estimator_even_with_ticket_reference(client: TestClient) -> None:
    user = register_user(client, "placement-haul-quote@example.com", "Pass12345!", "Placement Haul Quote")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Placement Haul Civil", "Placement Haul Project")
    tenant_id = onboarding["tenant_id"]

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "hauling-quote.txt",
                (
                    b"Vendor Quote\n"
                    b"Quote Number: CHS-081126-77\n"
                    b"Project: North Ridge Commerce Park Phase 2\n"
                    b"Assumed One-Way Distance: 16 miles\n"
                    b"Hourly Rate: 118\n"
                    b"Unit Price: 3.25\n"
                    b"Ticket Ref: TCK-4477\n"
                ),
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    item_id = upload.json()["id"]

    suggestions = client.post(
        "/api/intake/placement/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [item_id]},
    )
    assert suggestions.status_code == 200, suggestions.text
    suggestion = suggestions.json()["items"][0]
    assert suggestion["destination_key"] == "estimator"


def test_haul_ticket_routes_to_tickets(client: TestClient) -> None:
    user = register_user(client, "placement-haul-ticket@example.com", "Pass12345!", "Placement Haul Ticket")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Placement Ticket Civil", "Placement Ticket Project")
    tenant_id = onboarding["tenant_id"]

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "haul-ticket.txt",
                (
                    b"Ticket Number: TCK-9901\n"
                    b"Driver: Sam Load\n"
                    b"Truck: T-17\n"
                    b"Material: Base Rock\n"
                    b"Net Weight: 18.6\n"
                ),
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    item_id = upload.json()["id"]

    suggestions = client.post(
        "/api/intake/placement/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [item_id]},
    )
    assert suggestions.status_code == 200, suggestions.text
    suggestion = suggestions.json()["items"][0]
    assert suggestion["destination_key"] == "tickets"


def test_bid_package_classification_and_project_matching_use_connected_evidence(client: TestClient) -> None:
    user = register_user(client, "placement-bid-package@example.com", "Pass12345!", "Placement Bid Package")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Placement Package Civil", "North Ridge Commerce Park - Phase 2")
    tenant_id = onboarding["tenant_id"]

    create_project = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={
            "project_name": "North Ridge Commerce Park - Phase 2",
            "project_number": "NRCP-PH2",
            "customer": "North Ridge Development",
            "address": "2120 Commerce Park Dr",
            "project_manager": "Estimator Lead",
            "status": "active",
            "description": "Primary bid package project.",
        },
    )
    assert create_project.status_code == 201, create_project.text

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={
            "file": (
                "hauling-quote-abbrev.txt",
                (
                    b"Hauling / Disposal Quote\n"
                    b"Project: N. Ridge Commerce Pk Ph 2\n"
                    b"Project Number: NRCP-PH2\n"
                    b"Quote Number: HQ-24011\n"
                    b"Assumed One-Way Distance: 16 miles\n"
                    b"Truck and load terms are included for pricing context only.\n"
                ),
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    item_id = upload.json()["id"]

    suggestions = client.post(
        "/api/intake/placement/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [item_id]},
    )
    assert suggestions.status_code == 200, suggestions.text

    suggestion = suggestions.json()["items"][0]
    assert suggestion["destination_key"] == "estimator"
    assert suggestion["document_intelligence"]["primary_document_type"] == "hauling_disposal_quote"
    assert suggestion["document_intelligence"]["project_number"] == "NRCP-PH2"
    assert suggestion["project_match"]["matched_project_id"]
    assert suggestion["project_match"]["match_confidence"] >= 0.78
    assert suggestion["project_match"]["auto_associate"] is True
