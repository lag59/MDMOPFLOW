from fastapi.testclient import TestClient

from app.api.routes import admin as admin_routes
from app.schemas import AdminTenantCountTriplet

from .helpers import complete_onboarding, register_user


def _login_super_admin(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["tokens"]["access_token"]


def test_admin_data_count_reconciliation_matches_authoritative_counts(client: TestClient) -> None:
    owner = register_user(client, "reconcile-owner@example.com", "Pass12345!", "Reconcile Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Reconcile Co", "Reconcile Project")
    tenant_id = onboarding["tenant_id"]

    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id}

    ticket = client.post(
        "/api/tickets",
        headers=owner_headers,
        json={
            "project_id": onboarding["project_id"],
            "ticket_number": "REC-TCK-001",
            "truck": "TR-001",
            "driver": "Driver One",
            "material": "Aggregate",
            "status": "draft",
        },
    )
    assert ticket.status_code == 201, ticket.text

    super_token = _login_super_admin(client)
    response = client.get(
        f"/api/admin/diagnostics/data-count-reconciliation?tenant_id={tenant_id}",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["total_tenants"] == 1
    assert payload["mismatched_tenants"] == 0
    assert len(payload["items"]) == 1

    item = payload["items"][0]
    assert item["tenant_id"] == tenant_id
    assert item["is_reconciled"] is True
    assert item["discrepancies"] == []
    assert item["expected"] == item["actual"]


def test_admin_data_count_reconciliation_flags_discrepancy_without_correction(client: TestClient, monkeypatch) -> None:
    owner = register_user(client, "reconcile-mismatch-owner@example.com", "Pass12345!", "Reconcile Mismatch Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Reconcile Mismatch Co", "Reconcile Mismatch Project")
    tenant_id = onboarding["tenant_id"]

    original_reported = admin_routes._reported_tenant_counts

    def fake_reported_counts(db, scoped_tenant_id: str):
        counts = original_reported(db, scoped_tenant_id)
        if scoped_tenant_id == tenant_id:
            return AdminTenantCountTriplet(
                users=counts.users + 5,
                projects=counts.projects,
                tickets=counts.tickets,
            )
        return counts

    monkeypatch.setattr(admin_routes, "_reported_tenant_counts", fake_reported_counts)

    super_token = _login_super_admin(client)
    response = client.get(
        f"/api/admin/diagnostics/data-count-reconciliation?tenant_id={tenant_id}&expected_total_tenants=19&expected_total_users=27",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["mismatched_tenants"] == 1

    item = payload["items"][0]
    assert item["is_reconciled"] is False
    assert any("users expected=" in text for text in item["discrepancies"])
    assert item["expected"]["users"] != item["actual"]["users"]

    # Session fixture checks are validation only and must report mismatches.
    assert any(text.startswith("total_tenants expected=19") for text in payload["session_validation"]["discrepancies"])
    assert any(text.startswith("total_users expected=27") for text in payload["session_validation"]["discrepancies"])
