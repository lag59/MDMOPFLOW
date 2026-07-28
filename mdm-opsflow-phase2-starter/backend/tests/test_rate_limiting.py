from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import rate_limit_windows


def test_auth_login_is_rate_limited(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS_PER_WINDOW", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    rate_limit_windows.clear()
    try:
        first = client.post(
            "/api/auth/login",
            json={"email": "missing@example.com", "password": "WrongPass123!"},
        )
        assert first.status_code == 401

        second = client.post(
            "/api/auth/login",
            json={"email": "missing@example.com", "password": "WrongPass123!"},
        )
        assert second.status_code == 429
        assert second.json()["detail"] == "Too many requests"
        assert second.headers["Retry-After"]
    finally:
        rate_limit_windows.clear()