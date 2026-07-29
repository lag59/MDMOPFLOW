from fastapi.testclient import TestClient


def test_payroll_timecards_runs_and_summary_are_tenant_scoped(client: TestClient) -> None:
    owner_register_response = client.post(
        "/api/auth/register",
        json={"email": "payroll@example.com", "password": "Pass12345!", "display_name": "Payroll User"},
    )
    assert owner_register_response.status_code == 201, owner_register_response.text
    owner_token = owner_register_response.json()["tokens"]["access_token"]

    payroll_user_register_response = client.post(
        "/api/auth/register",
        json={"email": "payroll.member@example.com", "password": "Pass12345!", "display_name": "Payroll Member"},
    )
    assert payroll_user_register_response.status_code == 201, payroll_user_register_response.text
    payroll_token = payroll_user_register_response.json()["tokens"]["access_token"]

    onboarding_response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Payroll Co",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Payroll"],
            "invite_emails": [],
            "first_project_name": "Payroll Project",
        },
    )
    assert onboarding_response.status_code == 201, onboarding_response.text
    tenant_id = onboarding_response.json()["tenant_id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id}

    assign_response = client.post(
        "/api/tenant-users",
        headers=owner_headers,
        json={"email": "payroll.member@example.com", "role_name": "payroll"},
    )
    assert assign_response.status_code == 201, assign_response.text

    headers = {"Authorization": f"Bearer {payroll_token}", "X-Tenant-ID": tenant_id}

    employee_response = client.post(
        "/api/employees",
        headers=owner_headers,
        json={
            "name": "Avery Chen",
            "role_title": "Operator",
            "email": "avery@example.com",
            "phone": "555-0100",
            "department": "Field",
            "status": "active",
        },
    )
    assert employee_response.status_code == 201, employee_response.text
    employee_id = employee_response.json()["id"]

    project_response = client.get("/api/projects", headers=headers)
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()[0]["id"]

    timecard_response = client.post(
        "/api/payroll/timecards",
        headers=headers,
        json={
            "employee_id": employee_id,
            "project_id": project_id,
            "work_date": "2026-07-28T00:00:00Z",
            "regular_hours": "8.00",
            "overtime_hours": "2.00",
            "double_time_hours": "0.00",
            "cost_code": "EARTH-100",
            "work_description": "Haul and grading support",
            "status": "submitted",
        },
    )
    assert timecard_response.status_code == 201, timecard_response.text

    timecards_list = client.get("/api/payroll/timecards", headers=headers)
    assert timecards_list.status_code == 200, timecards_list.text
    assert len(timecards_list.json()) == 1
    assert timecards_list.json()[0]["employee_id"] == employee_id

    payroll_run_response = client.post(
        "/api/payroll/runs",
        headers=headers,
        json={
            "run_number": "PR-2026-001",
            "period_start": "2026-07-01T00:00:00Z",
            "period_end": "2026-07-31T23:59:59Z",
            "status": "draft",
            "notes": "July payroll run",
        },
    )
    assert payroll_run_response.status_code == 201, payroll_run_response.text
    run_payload = payroll_run_response.json()
    assert run_payload["employee_count"] == 1
    assert run_payload["total_regular_hours"] == "8.00"
    assert run_payload["total_overtime_hours"] == "2.00"

    summary_response = client.get("/api/payroll/summary", headers=headers)
    assert summary_response.status_code == 200, summary_response.text
    summary_payload = summary_response.json()
    assert summary_payload["employee_count"] == 1
    assert summary_payload["timecard_count"] == 1
    assert summary_payload["payroll_run_count"] == 1
    assert summary_payload["total_regular_hours"] == "8.00"
    assert summary_payload["total_overtime_hours"] == "2.00"
    assert summary_payload["by_project"][0]["project_id"] == project_id
