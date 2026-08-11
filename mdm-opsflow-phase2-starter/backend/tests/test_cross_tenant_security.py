from datetime import datetime, timezone

from fastapi.testclient import TestClient

from .helpers import complete_onboarding, register_user


def _headers(token: str, tenant_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_cross_tenant_security_guards_for_users_projects_estimates_tickets_reports_exports_and_search(client: TestClient) -> None:
    a_user = register_user(client, "iso-a@example.com", "Pass12345!", "Isolation A")
    b_user = register_user(client, "iso-b@example.com", "Pass12345!", "Isolation B")

    a_token = a_user["tokens"]["access_token"]
    b_token = b_user["tokens"]["access_token"]

    a_onboarding = complete_onboarding(client, a_token, "Isolation Company A", "Isolation A First")
    b_onboarding = complete_onboarding(client, b_token, "Isolation Company B", "Isolation B First")

    a_tenant_id = a_onboarding["tenant_id"]
    b_tenant_id = b_onboarding["tenant_id"]

    a_project_resp = client.post(
        "/api/projects",
        headers=_headers(a_token, a_tenant_id),
        json={
            "project_name": "A Secure Project",
            "project_number": "A-SEC-1",
            "customer": "A Customer",
            "address": "A Address",
            "project_manager": "A PM",
            "status": "active",
            "description": "A confidential project",
        },
    )
    assert a_project_resp.status_code == 201, a_project_resp.text
    a_project = a_project_resp.json()

    a_estimator_user = register_user(client, "iso-a-estimator@example.com", "Pass12345!", "Isolation A Estimator")
    assign_estimator = client.post(
        "/api/tenant-users",
        headers=_headers(a_token, a_tenant_id),
        json={
            "email": "iso-a-estimator@example.com",
            "role_name": "estimator",
            "display_name": "Isolation A Estimator",
            "title": "Estimator",
            "temporary_password": "Pass12345!",
        },
    )
    assert assign_estimator.status_code == 201, assign_estimator.text
    a_estimator_token = a_estimator_user["tokens"]["access_token"]

    a_estimate_resp = client.post(
        "/api/estimates",
        headers=_headers(a_estimator_token, a_tenant_id),
        json={
            "project_id": a_project["id"],
            "estimate_name": "A Estimate",
            "estimate_number": "EST-A-001",
            "customer_name": "A Customer",
            "project_name": "A Secure Project",
            "project_address": "A Address",
            "project_type": "Civil",
            "estimator_name": "A Estimator",
            "status": "Draft Estimate",
        },
    )
    assert a_estimate_resp.status_code == 201, a_estimate_resp.text
    a_estimate = a_estimate_resp.json()

    a_ticket_resp = client.post(
        "/api/tickets",
        headers=_headers(a_token, a_tenant_id),
        json={
            "project_id": a_project["id"],
            "ticket_number": "A-TCK-001",
            "truck": "A-TRK",
            "driver": "A Driver",
            "material": "Base",
            "status": "draft",
        },
    )
    assert a_ticket_resp.status_code == 201, a_ticket_resp.text
    a_ticket = a_ticket_resp.json()

    a_report_resp = client.post(
        "/api/daily-field-reports",
        headers=_headers(a_token, a_tenant_id),
        json={
            "project_id": a_project["id"],
            "report_date": datetime.now(timezone.utc).isoformat(),
            "reporting_supervisor": "A Supervisor",
            "work_performed": "A work",
        },
    )
    assert a_report_resp.status_code == 201, a_report_resp.text
    a_report = a_report_resp.json()

    cross_tenant_users = client.get(
        "/api/tenant-users",
        headers=_headers(b_token, a_tenant_id),
    )
    assert cross_tenant_users.status_code == 403

    cross_tenant_project_get = client.get(
        f"/api/projects/{a_project['id']}",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_project_get.status_code == 404

    cross_tenant_project_list = client.get(
        f"/api/projects?tenant_id={a_tenant_id}",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_project_list.status_code == 403

    cross_tenant_estimate_get = client.get(
        f"/api/estimates/{a_estimate['id']}",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_estimate_get.status_code == 404

    cross_tenant_ticket_get = client.get(
        f"/api/tickets/{a_ticket['id']}",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_ticket_get.status_code == 404

    cross_tenant_ticket_list = client.get(
        f"/api/tickets?tenant_id={a_tenant_id}",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_ticket_list.status_code == 403

    cross_tenant_report_pdf = client.get(
        f"/api/daily-field-reports/{a_report['id']}/pdf",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_report_pdf.status_code == 404

    create_export_token = client.post(
        "/api/intake/events/replay-history/export-token"
        f"?tenant_id={a_tenant_id}&output=json&limit=10",
        headers=_headers(a_token, a_tenant_id),
    )
    assert create_export_token.status_code == 200, create_export_token.text

    cross_tenant_export_token = client.post(
        "/api/intake/events/replay-history/export-token"
        f"?tenant_id={a_tenant_id}&output=json&limit=10",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_export_token.status_code == 403

    cross_tenant_history_search = client.get(
        f"/api/intake/events/replay-history/export-token-history?tenant_id={a_tenant_id}&limit=20",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_history_search.status_code == 403

    cross_tenant_replay_history = client.get(
        f"/api/intake/events/replay-history?tenant_id={a_tenant_id}&limit=20",
        headers=_headers(b_token, b_tenant_id),
    )
    assert cross_tenant_replay_history.status_code == 403
