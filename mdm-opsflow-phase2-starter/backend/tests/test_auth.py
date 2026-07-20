from fastapi.testclient import TestClient


def test_auth_register_login_me_refresh_logout(client: TestClient):
    payload = {
        "email": "auth-user@example.com",
        "password": "Pass12345!",
        "display_name": "Auth User",
    }

    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["email"] == payload["email"]
    assert register_data["tokens"]["access_token"]
    assert register_data["tokens"]["refresh_token"]

    login_response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    access_token = login_data["tokens"]["access_token"]
    refresh_token = login_data["tokens"]["refresh_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == payload["email"]

    refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]

    logout_response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout_response.status_code == 204

    refresh_after_logout = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_after_logout.status_code == 401


def test_platform_admin_is_seeded_and_protected(client: TestClient):
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    overview = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert overview.status_code == 200
    assert overview.json()["role"] == "platform_super_admin"

    user_register = client.post(
        "/api/auth/register",
        json={"email": "regular@example.com", "password": "Pass12345!", "display_name": "Regular"},
    )
    user_token = user_register.json()["tokens"]["access_token"]

    denied = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {user_token}"})
    assert denied.status_code == 403
