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


def test_ticket_quantity_calculation_derives_quantities_and_costs(client: TestClient) -> None:
    headers = _auth_headers(client, "calc1@example.com")

    response = client.post(
        "/api/tickets/quantity-calculation",
        headers=headers,
        json={
            "gross_weight_lbs": "54000",
            "tare_weight_lbs": "32000",
            "number_of_loads": 4,
            "material_density_tons_per_cubic_yard": "1.5",
            "rate_per_ton": "12.5",
            "rate_per_cubic_yard": "18",
            "rate_per_load": "65",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["net_weight_lbs"] == "22000.00"
    assert payload["net_tons"] == "11.00"
    assert payload["estimated_cubic_yards"] == "7.33"
    assert payload["tons_per_load"] == "2.75"
    assert payload["cubic_yards_per_load"] == "1.83"
    assert payload["cost_from_ton"] == "137.50"
    assert payload["cost_from_cubic_yard"] == "132.00"
    assert payload["cost_from_load"] == "260.00"
    assert payload["selected_cost_method"] == "per_ton"
    assert payload["selected_total_cost"] == "137.50"
    assert "net_weight_lbs derived from gross_weight_lbs - tare_weight_lbs" in payload["assumptions"]


def test_ticket_quantity_calculation_estimates_loads_from_capacity(client: TestClient) -> None:
    headers = _auth_headers(client, "calc2@example.com")

    response = client.post(
        "/api/tickets/quantity-calculation",
        headers=headers,
        json={
            "net_weight_lbs": "30000",
            "truck_capacity_tons": "15",
            "rate_per_load": "95",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["net_tons"] == "15.00"
    assert payload["estimated_load_count"] == "1.00"
    assert payload["cost_from_load"] == "95.00"
    assert payload["selected_cost_method"] == "per_load"
    assert payload["selected_total_cost"] == "95.00"
    assert "estimated_load_count derived from net_tons / truck_capacity_tons" in payload["assumptions"]


def test_ticket_quantity_calculation_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/tickets/quantity-calculation", json={"net_weight_lbs": "5000"})
    assert response.status_code == 401
