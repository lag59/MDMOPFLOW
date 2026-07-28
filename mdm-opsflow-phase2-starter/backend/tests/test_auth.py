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

    update_me_response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"display_name": "Updated Auth User", "title": "PM"},
    )
    assert update_me_response.status_code == 200
    assert update_me_response.json()["display_name"] == "Updated Auth User"
    assert update_me_response.json()["title"] == "PM"

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


def test_super_admin_can_manage_user_access_and_reset_password(client: TestClient):
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    user_register = client.post(
        "/api/auth/register",
        json={"email": "managed-user@example.com", "password": "Pass12345!", "display_name": "Managed User"},
    )
    assert user_register.status_code == 201
    user_id = user_register.json()["user_id"]

    users_list = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_list.status_code == 200
    assert any(row["email"] == "managed-user@example.com" for row in users_list.json())

    access_update = client.patch(
        f"/api/admin/users/{user_id}/access",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"platform_role": "platform_super_admin", "is_active": True},
    )
    assert access_update.status_code == 200
    assert access_update.json()["platform_role"] == "platform_super_admin"

    password_reset = client.post(
        f"/api/admin/users/{user_id}/reset-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_password": "ResetPass123!"},
    )
    assert password_reset.status_code == 200

    old_login = client.post(
        "/api/auth/login",
        json={"email": "managed-user@example.com", "password": "Pass12345!"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"email": "managed-user@example.com", "password": "ResetPass123!"},
    )
    assert new_login.status_code == 200
