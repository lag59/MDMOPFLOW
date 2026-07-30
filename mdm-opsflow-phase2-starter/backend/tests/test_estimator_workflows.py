from fastapi.testclient import TestClient


def test_estimator_domain_workflows_and_permissions(client: TestClient) -> None:
    owner_register_response = client.post(
        "/api/auth/register",
        json={"email": "estimator.owner@example.com", "password": "Pass12345!", "display_name": "Estimator Owner"},
    )
    assert owner_register_response.status_code == 201, owner_register_response.text
    owner_token = owner_register_response.json()["tokens"]["access_token"]

    estimator_register_response = client.post(
        "/api/auth/register",
        json={"email": "estimator.member@example.com", "password": "Pass12345!", "display_name": "Estimator Member"},
    )
    assert estimator_register_response.status_code == 201, estimator_register_response.text
    estimator_token = estimator_register_response.json()["tokens"]["access_token"]

    accounting_register_response = client.post(
        "/api/auth/register",
        json={"email": "estimator.accounting@example.com", "password": "Pass12345!", "display_name": "Accounting Member"},
    )
    assert accounting_register_response.status_code == 201, accounting_register_response.text
    accounting_token = accounting_register_response.json()["tokens"]["access_token"]

    onboarding_response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Estimator Co",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Tickets"],
            "invite_emails": [],
            "first_project_name": "Estimator Project",
        },
    )
    assert onboarding_response.status_code == 201, onboarding_response.text
    tenant_id = onboarding_response.json()["tenant_id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id}

    assign_estimator = client.post(
        "/api/tenant-users",
        headers=owner_headers,
        json={"email": "estimator.member@example.com", "role_name": "estimator"},
    )
    assert assign_estimator.status_code == 201, assign_estimator.text

    assign_accounting = client.post(
        "/api/tenant-users",
        headers=owner_headers,
        json={"email": "estimator.accounting@example.com", "role_name": "accounting"},
    )
    assert assign_accounting.status_code == 201, assign_accounting.text

    estimator_headers = {"Authorization": f"Bearer {estimator_token}", "X-Tenant-ID": tenant_id}
    accounting_headers = {"Authorization": f"Bearer {accounting_token}", "X-Tenant-ID": tenant_id}

    project_response = client.get("/api/projects", headers=owner_headers)
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()[0]["id"]

    takeoff_response = client.post(
        "/api/estimator/takeoffs",
        headers=estimator_headers,
        json={
            "project_id": project_id,
            "takeoff_number": "TK-001",
            "material_name": "Aggregate Base",
            "quantity": "120.50",
            "unit_of_measure": "cy",
            "estimated_cost": "18750.00",
            "status": "draft",
            "notes": "Initial civil quantities",
        },
    )
    assert takeoff_response.status_code == 201, takeoff_response.text

    version_response = client.post(
        "/api/estimator/versions",
        headers=estimator_headers,
        json={
            "project_id": project_id,
            "version_name": "Bid Rev A",
            "revision_number": 1,
            "estimated_revenue": "340000.00",
            "estimated_cost": "278000.00",
            "status": "submitted",
            "notes": "First pricing pass",
        },
    )
    assert version_response.status_code == 201, version_response.text

    bid_response = client.post(
        "/api/estimator/bid-pipeline",
        headers=estimator_headers,
        json={
            "project_id": project_id,
            "bid_number": "BID-9001",
            "customer_name": "City Utilities",
            "stage": "proposal",
            "bid_amount": "340000.00",
            "probability_percent": "62.50",
            "due_date": "2026-08-15T00:00:00Z",
            "status": "open",
            "notes": "Pending clarifications",
        },
    )
    assert bid_response.status_code == 201, bid_response.text
    bid_id = bid_response.json()["id"]

    win_loss_response = client.post(
        "/api/estimator/win-loss",
        headers=estimator_headers,
        json={
            "project_id": project_id,
            "bid_pipeline_item_id": bid_id,
            "outcome": "won",
            "final_amount": "336500.00",
            "decision_date": "2026-08-20T00:00:00Z",
            "reason": "Strong schedule and safety plan",
        },
    )
    assert win_loss_response.status_code == 201, win_loss_response.text

    summary_response = client.get("/api/estimator/summary", headers=estimator_headers)
    assert summary_response.status_code == 200, summary_response.text
    summary_payload = summary_response.json()
    assert summary_payload["takeoff_count"] == 1
    assert summary_payload["version_count"] == 1
    assert summary_payload["bid_pipeline_count"] == 1
    assert summary_payload["wins"] == 1
    assert summary_payload["losses"] == 0
    assert summary_payload["win_rate_percent"] == "100.00"

    estimate_response = client.post(
        "/api/estimates",
        headers=estimator_headers,
        json={
            "project_id": project_id,
            "estimate_name": "North Yard Bid",
            "estimate_number": "EST-1001",
            "customer_name": "City Utilities",
            "project_name": "North Yard",
            "project_address": "100 Main St",
            "project_type": "Heavy civil",
            "estimator_name": "Estimator Member",
            "project_manager_name": "Jordan PM",
            "contract_type": "Lump sum",
            "estimate_type": "Bid",
            "currency": "USD",
            "target_margin_percent": "15.00",
            "default_overhead_percent": "8.00",
            "default_contingency_percent": "5.00",
            "notes": "Initial estimate",
            "status": "New",
        },
    )
    assert estimate_response.status_code == 201, estimate_response.text
    estimate_id = estimate_response.json()["id"]

    estimate_item_response = client.post(
        f"/api/estimates/{estimate_id}/items",
        headers=estimator_headers,
        json={
            "item_number": "1",
            "cost_code": "31-23-16",
            "division": "Sitework",
            "phase": "Earthwork",
            "description": "Mass excavation",
            "quantity": "20000.00",
            "unit_of_measure": "CY",
            "unit_cost": "4.50",
            "total_cost": "90000.00",
            "unit_price": "5.25",
            "total_selling_price": "105000.00",
            "source": "manual",
            "review_status": "accepted",
        },
    )
    assert estimate_item_response.status_code == 201, estimate_item_response.text

    validate_response = client.post(f"/api/estimates/{estimate_id}/validate", headers=estimator_headers)
    assert validate_response.status_code == 200, validate_response.text
    assert "completion_score" in validate_response.json()

    submit_response = client.post(f"/api/estimates/{estimate_id}/submit", headers=estimator_headers)
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json()["status"] == "Submitted"

    approve_response = client.post(
        f"/api/estimates/{estimate_id}/approve",
        headers=estimator_headers,
        json={"decision": "approved", "comments": "Reviewed and approved"},
    )
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["decision"] == "approved"

    patch_awarded_response = client.patch(
        f"/api/estimates/{estimate_id}",
        headers=estimator_headers,
        json={"notes": "Award confirmed"},
    )
    assert patch_awarded_response.status_code == 409, patch_awarded_response.text

    ai_review_response = client.post(f"/api/estimates/{estimate_id}/ai-review", headers=estimator_headers)
    assert ai_review_response.status_code == 200, ai_review_response.text

    convert_response = client.post(f"/api/estimates/{estimate_id}/convert-to-project", headers=owner_headers)
    assert convert_response.status_code == 200, convert_response.text
    assert convert_response.json()["status"] == "Converted to Project"

    audit_logs_response = client.get(f"/api/estimates/{estimate_id}/audit-logs", headers=estimator_headers)
    assert audit_logs_response.status_code == 200, audit_logs_response.text
    assert len(audit_logs_response.json()) >= 4

    list_takeoffs_response = client.get("/api/estimator/takeoffs", headers=accounting_headers)
    assert list_takeoffs_response.status_code == 200, list_takeoffs_response.text
    assert len(list_takeoffs_response.json()) == 1

    create_takeoff_forbidden = client.post(
        "/api/estimator/takeoffs",
        headers=accounting_headers,
        json={
            "project_id": project_id,
            "takeoff_number": "TK-002",
            "material_name": "Structural Fill",
            "quantity": "20.00",
            "unit_of_measure": "cy",
            "status": "draft",
            "notes": "Should fail for accounting",
        },
    )
    assert create_takeoff_forbidden.status_code == 403, create_takeoff_forbidden.text
