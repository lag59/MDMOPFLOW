from __future__ import annotations

from fastapi.testclient import TestClient

from .helpers import complete_onboarding, register_user


def test_duplicate_upload_is_flagged_and_review_queue_filters_results(client: TestClient) -> None:
    user = register_user(client, "dup-review@example.com", "Pass12345!", "Duplicate Reviewer")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Duplicate Civil", "Duplicate Project")
    tenant_id = onboarding["tenant_id"]

    payload = (
        b"Ticket: TCK-7777\n"
        b"Driver: Riley Ford\n"
        b"Truck: Unit 7\n"
        b"Material: Asphalt\n"
    )

    first_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-7777.txt", payload, "text/plain")},
    )
    assert first_upload.status_code == 201
    first_item = first_upload.json()
    assert first_item["duplicate_of_item_id"] is None
    assert first_item["needs_review"] is False

    second_upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        files={"file": ("ticket-7777-copy.txt", payload, "text/plain")},
    )
    assert second_upload.status_code == 201
    second_item = second_upload.json()

    assert second_item["duplicate_of_item_id"] == first_item["id"]
    assert second_item["needs_review"] is True
    assert second_item["status"] == "reviewing"
    assert first_item["id"] in second_item["review_reason"]

    review_queue_response = client.get(
        "/api/intake/items",
        params={"review_queue": "true"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert review_queue_response.status_code == 200
    queued_items = review_queue_response.json()

    assert len(queued_items) == 1
    assert queued_items[0]["id"] == second_item["id"]
