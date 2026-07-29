from datetime import date

from fastapi.testclient import TestClient

from .helpers import complete_onboarding, register_user


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    user = register_user(client, email, "Pass12345!", "Ops User")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, f"{email}-tenant", "First Project")
    tenant_id = onboarding["tenant_id"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


def test_daily_field_reports_create_submit_and_approve_workflow(client: TestClient) -> None:
    headers = _auth_headers(client, "dailyreport1@example.com")

    project_response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "project_name": "River Front Lift",
            "project_number": "PRJ-9001",
            "customer": "City of Example",
            "address": "100 Main St",
            "project_manager": "Alex Ramos",
            "status": "active",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    report_response = client.post(
        "/api/daily-field-reports",
        headers=headers,
        json={
            "project_id": project_id,
            "report_date": date.today().isoformat(),
            "reporting_supervisor": "Jordan Lee",
            "company_name": "Acme Civil",
            "shift_start_time": "06:00",
            "shift_end_time": "14:00",
            "weather": {"conditions": "Clear"},
            "work_performed": "Grading and hauling",
            "work_planned_for_tomorrow": "Continue grading",
        },
    )

    assert report_response.status_code == 201
    payload = report_response.json()
    assert payload["project_id"] == project_id
    assert payload["status"] == "draft"
    assert payload["report_number"].startswith("DR-")

    list_response = client.get(f"/api/daily-field-reports?project_id={project_id}", headers=headers)
    assert list_response.status_code == 200
    reports = list_response.json()
    assert len(reports) == 1

    submit_response = client.post(f"/api/daily-field-reports/{payload['id']}/submit", headers=headers)
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"

    approve_response = client.post(f"/api/daily-field-reports/{payload['id']}/approve", headers=headers)
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


def test_daily_field_reports_support_review_and_return_workflow(client: TestClient) -> None:
    headers = _auth_headers(client, "dailyreport4@example.com")

    project_response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "project_name": "Blue Mesa",
            "project_number": "PRJ-9004",
            "customer": "Blue Mesa LLC",
            "address": "400 Oak St",
            "project_manager": "Morgan Chen",
            "status": "active",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    report_response = client.post(
        "/api/daily-field-reports",
        headers=headers,
        json={
            "project_id": project_id,
            "report_date": date.today().isoformat(),
            "reporting_supervisor": "Jamie Ross",
            "company_name": "Acme Civil",
            "shift_start_time": "06:00",
            "shift_end_time": "14:00",
        },
    )
    assert report_response.status_code == 201
    report_id = report_response.json()["id"]

    review_response = client.post(f"/api/daily-field-reports/{report_id}/review", headers=headers)
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "reviewed"

    return_response = client.post(f"/api/daily-field-reports/{report_id}/return", headers=headers)
    assert return_response.status_code == 200
    assert return_response.json()["status"] == "returned"


def test_daily_field_reports_support_sections_and_pdf_export(client: TestClient) -> None:
    headers = _auth_headers(client, "dailyreport3@example.com")

    project_response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "project_name": "Cedar Point",
            "project_number": "PRJ-9003",
            "customer": "Cedar Point LLC",
            "address": "300 Pine Rd",
            "project_manager": "Morgan Chen",
            "status": "active",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    report_response = client.post(
        "/api/daily-field-reports",
        headers=headers,
        json={
            "project_id": project_id,
            "report_date": date.today().isoformat(),
            "reporting_supervisor": "Jordan Lee",
            "company_name": "Acme Civil",
            "shift_start_time": "06:00",
            "shift_end_time": "14:00",
            "weather": {"conditions": "Cloudy", "temperature_high": 82},
            "crew_members": [{"name": "Alex", "trade": "Operator", "regular_hours": 8.0}],
            "equipment_used": [{"name": "Excavator 1", "operator": "Alex", "operating_hours": 8.0}],
            "deliveries": [{"supplier": "Acme Supply", "material": "Stone", "quantity": 50, "unit": "tons"}],
            "visitors": [{"name": "Owner Rep", "role": "Owner"}],
            "delays": [{"category": "Weather", "description": "Heavy rain", "duration_hours": 2.5}],
            "photos": [{"description": "Site progress", "classification": "progress"}],
            "production_quantities": [{"bid_item": "Excavation", "quantity_completed_today": 125.0, "unit_of_measure": "cubic_yards"}],
            "safety_observations": [{"observation_type": "hazard", "description": "Loose material", "severity": "medium"}],
            "work_performed": "Grading and hauling",
            "work_planned_for_tomorrow": "Continue grading",
            "prepared_by": "Jordan Lee",
            "electronic_signature": "Jordan Lee",
        },
    )

    assert report_response.status_code == 201
    payload = report_response.json()
    assert payload["crew_members"][0]["name"] == "Alex"
    assert payload["prepared_by"] == "Jordan Lee"

    pdf_response = client.get(f"/api/daily-field-reports/{payload['id']}/pdf", headers=headers)
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert b"Labor Hours Total" in pdf_response.content
    assert b"Machine Hours Total" in pdf_response.content
    assert b"Material Used Total" in pdf_response.content


def test_daily_field_reports_block_duplicate_reports_for_same_shift(client: TestClient) -> None:
    headers = _auth_headers(client, "dailyreport2@example.com")

    project_response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "project_name": "North Ridge",
            "project_number": "PRJ-9002",
            "customer": "North Ridge LLC",
            "address": "200 Oak Ave",
            "project_manager": "Taylor Brooks",
            "status": "active",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    first_response = client.post(
        "/api/daily-field-reports",
        headers=headers,
        json={
            "project_id": project_id,
            "report_date": date.today().isoformat(),
            "reporting_supervisor": "Jordan Lee",
            "company_name": "Acme Civil",
            "shift_start_time": "06:00",
            "shift_end_time": "14:00",
        },
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/daily-field-reports",
        headers=headers,
        json={
            "project_id": project_id,
            "report_date": date.today().isoformat(),
            "reporting_supervisor": "Jordan Lee",
            "company_name": "Acme Civil",
            "shift_start_time": "06:00",
            "shift_end_time": "14:00",
        },
    )

    assert duplicate_response.status_code == 409
