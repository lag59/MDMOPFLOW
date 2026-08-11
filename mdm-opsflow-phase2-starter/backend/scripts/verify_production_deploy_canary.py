from __future__ import annotations

import json
import os
import uuid
from datetime import date
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "https://mdmopflow-production-cd89.up.railway.app"
DEFAULT_PASSWORD = "Pass12345!"


def _call(
    base_url: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    url = f"{base_url}{path}"
    payload_bytes = None
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if body is not None:
        payload_bytes = json.dumps(body).encode("utf-8")

    req = request.Request(url, data=payload_bytes, headers=request_headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else None
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            body_payload = json.loads(text) if text else None
        except Exception:
            body_payload = {"raw": text}
        return exc.code, body_payload


def main() -> int:
    base_url = (os.getenv("OPSFLOW_CANARY_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    password = os.getenv("OPSFLOW_CANARY_PASSWORD") or DEFAULT_PASSWORD

    suffix = uuid.uuid4().hex[:10]
    email = f"canary.deploy.{suffix}@example.com"
    results: dict[str, Any] = {"base_url": base_url, "email": email}

    status, payload = _call(
        base_url,
        "POST",
        "/api/auth/register",
        {
            "email": email,
            "password": password,
            "display_name": "Deploy Canary User",
        },
    )
    results["register"] = status
    if status != 201:
        results["register_payload"] = payload
        print(json.dumps(results, indent=2))
        return 1

    token = payload["tokens"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    status, payload = _call(
        base_url,
        "POST",
        "/api/onboarding/complete",
        {
            "company_name": f"Deploy Canary Tenant {suffix}",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": "Deploy Canary Project",
        },
        headers=auth_headers,
    )
    results["onboarding"] = status
    if status != 201:
        results["onboarding_payload"] = payload
        print(json.dumps(results, indent=2))
        return 1

    tenant_id = payload["tenant_id"]
    tenant_headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }

    status, payload = _call(
        base_url,
        "POST",
        "/api/projects",
        {
            "project_name": f"Deploy Canary FS {suffix}",
            "project_number": f"DC-{suffix}",
            "customer": "Deploy Canary",
            "address": "100 Main St, Austin, TX",
            "project_manager": "Deploy Canary",
            "status": "active",
        },
        headers=tenant_headers,
    )
    results["project_create"] = status
    if status != 201:
        results["project_payload"] = payload
        print(json.dumps(results, indent=2))
        return 1

    project_id = payload["id"]

    status, payload = _call(
        base_url,
        "POST",
        "/api/daily-field-reports/assist",
        {
            "project_id": project_id,
            "report_date": date.today().isoformat(),
            "reporting_supervisor": "Deploy Canary Foreman",
            "total_workers": 3,
            "weather": {"condition": "Clear"},
            "work_performed": "",
            "equipment_used": [{"name": "Excavator", "hours": 8}],
        },
        headers=tenant_headers,
    )
    results["assist"] = status
    if status != 200:
        results["assist_payload"] = payload
        print(json.dumps(results, indent=2))
        return 1

    status, payload = _call(base_url, "GET", "/api/tickets", headers=tenant_headers)
    results["tickets_list"] = status
    if status != 200:
        results["tickets_payload"] = payload
        print(json.dumps(results, indent=2))
        return 1

    print(json.dumps(results, indent=2))
    print("Deploy canary passed: /api/daily-field-reports/assist and /api/tickets are healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
