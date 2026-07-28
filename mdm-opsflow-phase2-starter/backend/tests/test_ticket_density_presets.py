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


def test_material_density_preset_crud(client: TestClient) -> None:
    headers = _auth_headers(client, "density1@example.com")

    upsert = client.put(
        "/api/tickets/material-density-presets/Crushed Stone",
        headers=headers,
        json={"density_tons_per_cubic_yard": "1.45"},
    )
    assert upsert.status_code == 200
    assert upsert.json()["material_name"] == "Crushed Stone"
    assert upsert.json()["density_tons_per_cubic_yard"] == "1.4500"

    listed = client.get("/api/tickets/material-density-presets", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["material_name"] == "Crushed Stone"

    deleted = client.delete("/api/tickets/material-density-presets/Crushed Stone", headers=headers)
    assert deleted.status_code == 204

    listed_after = client.get("/api/tickets/material-density-presets", headers=headers)
    assert listed_after.status_code == 200
    assert listed_after.json() == []


def test_quantity_calculation_resolves_density_from_tenant_preset(client: TestClient) -> None:
    headers = _auth_headers(client, "density2@example.com")

    upsert = client.put(
        "/api/tickets/material-density-presets/Top Soil",
        headers=headers,
        json={"density_tons_per_cubic_yard": "1.20"},
    )
    assert upsert.status_code == 200

    response = client.post(
        "/api/tickets/quantity-calculation",
        headers=headers,
        json={
            "net_weight_lbs": "24000",
            "material_name": "top soil",
            "number_of_loads": 2,
            "rate_per_load": "110",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["net_tons"] == "12.00"
    assert payload["estimated_cubic_yards"] == "10.00"
    assert payload["resolved_density_source"] == "preset"
    assert payload["resolved_material_name"] == "Top Soil"


def test_ticket_create_auto_standardizes_tons_and_volume_from_weight_and_preset(client: TestClient) -> None:
    headers = _auth_headers(client, "density3@example.com")

    upsert = client.put(
        "/api/tickets/material-density-presets/Aggregate",
        headers=headers,
        json={"density_tons_per_cubic_yard": "1.50"},
    )
    assert upsert.status_code == 200

    create_response = client.post(
        "/api/tickets",
        headers=headers,
        json={
            "ticket_number": "TCK-CALC-1",
            "material": "Aggregate",
            "weight": "22000",
            "status": "draft",
        },
    )
    assert create_response.status_code == 201
    ticket = create_response.json()
    assert ticket["tons"] == "11.00"
    assert ticket["volume_yards"] == "7.33"


def test_ticket_update_auto_standardizes_tons_and_volume_from_weight_and_preset(client: TestClient) -> None:
    headers = _auth_headers(client, "density4@example.com")

    upsert = client.put(
        "/api/tickets/material-density-presets/Sand",
        headers=headers,
        json={"density_tons_per_cubic_yard": "1.25"},
    )
    assert upsert.status_code == 200

    create_response = client.post(
        "/api/tickets",
        headers=headers,
        json={
            "ticket_number": "TCK-CALC-2",
            "material": "Sand",
            "status": "draft",
        },
    )
    assert create_response.status_code == 201
    ticket_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/tickets/{ticket_id}",
        headers=headers,
        json={
            "weight": "25000",
            "material": "Sand",
        },
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["tons"] == "12.50"
    assert updated["volume_yards"] == "10.00"
