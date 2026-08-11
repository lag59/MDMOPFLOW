from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _past_iso(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _future_iso(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _admin_token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200
    return response.json()["tokens"]["access_token"]


def test_cleanup_dry_run_then_apply_deactivates_only_expired_test_data(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={
            "email": "cleanup-target@example.com",
            "password": "Pass12345!",
            "display_name": "Cleanup Target",
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "cleanup-it-001",
            "expires_at": _past_iso(),
        },
    )
    assert register.status_code == 201
    user_token = register.json()["tokens"]["access_token"]

    onboarding = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "company_name": "Cleanup Test Tenant",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": "Cleanup Project",
            "tenant_type": "test",
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "cleanup-it-001",
            "expires_at": _past_iso(),
        },
    )
    assert onboarding.status_code == 201

    admin_token = _admin_token(client)

    dry_run = client.post(
        "/api/admin/test-data/cleanup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    dry_data = dry_run.json()
    assert dry_data["dry_run"] is True
    assert dry_data["eligible_tenants"] == 1
    assert dry_data["eligible_users"] == 1
    assert dry_data["deactivated_memberships"] >= 1

    before_apply = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert before_apply.status_code == 200
    target_before = next(row for row in before_apply.json() if row["email"] == "cleanup-target@example.com")
    assert target_before["is_active"] is True

    apply_run = client.post(
        "/api/admin/test-data/cleanup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"dry_run": False},
    )
    assert apply_run.status_code == 200, apply_run.text
    apply_data = apply_run.json()
    assert apply_data["dry_run"] is False
    assert apply_data["deactivated_memberships"] >= 1
    assert apply_data["deactivated_users"] >= 1
    assert apply_data["preserved_audit_logs"] is True

    after_apply = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert after_apply.status_code == 200
    target_after = next(row for row in after_apply.json() if row["email"] == "cleanup-target@example.com")
    assert target_after["is_active"] is False


def test_cleanup_never_targets_production_or_demo_tenants_even_if_expired_and_marked_test(client: TestClient) -> None:
    register_prod = client.post(
        "/api/auth/register",
        json={
            "email": "prod-protected@example.com",
            "password": "Pass12345!",
            "display_name": "Prod Protected",
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "cleanup-it-002",
            "expires_at": _past_iso(),
        },
    )
    assert register_prod.status_code == 201
    prod_token = register_prod.json()["tokens"]["access_token"]

    onboarding_prod = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {prod_token}"},
        json={
            "company_name": "Production Protected Tenant",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": "Production Protected Project",
            "tenant_type": "production",
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "cleanup-it-002",
            "expires_at": _past_iso(),
        },
    )
    assert onboarding_prod.status_code == 201

    register_demo = client.post(
        "/api/auth/register",
        json={
            "email": "demo-protected@example.com",
            "password": "Pass12345!",
            "display_name": "Demo Protected",
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "cleanup-it-003",
            "expires_at": _future_iso(),
        },
    )
    assert register_demo.status_code == 201
    demo_token = register_demo.json()["tokens"]["access_token"]

    onboarding_demo = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {demo_token}"},
        json={
            "company_name": "Demo Protected Tenant",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": "Demo Protected Project",
            "tenant_type": "demo",
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "cleanup-it-003",
            "expires_at": _past_iso(),
        },
    )
    assert onboarding_demo.status_code == 201

    admin_token = _admin_token(client)
    run_cleanup = client.post(
        "/api/admin/test-data/cleanup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"dry_run": False},
    )
    assert run_cleanup.status_code == 200, run_cleanup.text

    tenant_actions = run_cleanup.json()["tenant_actions"]
    tenant_names = {item["tenant_name"] for item in tenant_actions}
    assert "Production Protected Tenant" not in tenant_names
    assert "Demo Protected Tenant" not in tenant_names

    users_after = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_after.status_code == 200
    prod_user = next(row for row in users_after.json() if row["email"] == "prod-protected@example.com")
    demo_user = next(row for row in users_after.json() if row["email"] == "demo-protected@example.com")
    assert prod_user["is_active"] is True
    assert demo_user["is_active"] is True
