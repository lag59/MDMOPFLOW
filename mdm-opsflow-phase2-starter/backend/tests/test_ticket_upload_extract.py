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


def test_ticket_upload_extract_prefills_calculator_from_text(client: TestClient) -> None:
    headers = _auth_headers(client, "upload1@example.com")

    response = client.post(
        "/api/tickets/upload-extract",
        headers=headers,
        files=[
            (
                "files",
                (
                    "ticket_upload.txt",
                    b"Ticket # TCK-901\nDriver: Jordan\nTruck: Unit 7\nMaterial: Aggregate\nNet weight: 22000 lbs\nLoads: 3",
                    "text/plain",
                ),
            )
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["extracted_entities"]["ticket_number"] == "TCK-901"
    assert item["extracted_entities"]["material"] == "Aggregate"
    assert item["calculator_prefill"]["net_weight_lbs"] == "22000"
    assert item["calculator_prefill"]["number_of_loads"] == 3
    assert isinstance(item["extraction_confidence"], float)
    assert item["review_required"] in (True, False)


def test_ticket_upload_extract_can_auto_create_draft_tickets(client: TestClient) -> None:
    headers = _auth_headers(client, "upload2@example.com")

    create_response = client.post(
        "/api/tickets/upload-extract?create_tickets=true",
        headers=headers,
        files=[
            (
                "files",
                (
                    "ticket_upload2.txt",
                    b"Ticket # TCK-902\nDriver: Alex\nTruck: Unit 9\nMaterial: Sand\nNet weight: 25000 lbs",
                    "text/plain",
                ),
            )
        ],
    )

    assert create_response.status_code == 200
    created_payload = create_response.json()
    assert len(created_payload["items"]) == 1
    assert created_payload["items"][0]["created_ticket_id"] is not None

    list_response = client.get("/api/tickets", headers=headers)
    assert list_response.status_code == 200
    tickets = list_response.json()
    assert len(tickets) == 1
    assert tickets[0]["ticket_number"] == "TCK-902"
    assert tickets[0]["material"] == "Sand"
    assert tickets[0]["weight"] == "25000.00"
    assert tickets[0]["tons"] == "12.50"


def test_ticket_upload_extract_invoice_style_text_extracts_ticket_fallback_and_material(client: TestClient) -> None:
    headers = _auth_headers(client, "upload3@example.com")

    response = client.post(
        "/api/tickets/upload-extract?create_tickets=true",
        headers=headers,
        files=[
            (
                "files",
                (
                    "invoice_62126.txt",
                    b"Invoice Number: INV-62126\nDescription: Dirt haul off\nQuantity: 2\nNet Weight: 18000 lbs",
                    "text/plain",
                ),
            )
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["extracted_entities"]["ticket_number"] == "INV-62126"
    assert item["extracted_entities"]["material"] == "Dirt haul off"
    assert item["calculator_prefill"]["number_of_loads"] == 2
    assert item["created_ticket_id"] is not None


def test_ticket_upload_extract_invoice_filename_fallback_generates_ticket_reference(client: TestClient) -> None:
    headers = _auth_headers(client, "upload4@example.com")

    response = client.post(
        "/api/tickets/upload-extract",
        headers=headers,
        files=[
            (
                "files",
                (
                    "Invoice_ 6_21_26.pdf",
                    b"No structured ticket labels in this sample.",
                    "application/pdf",
                ),
            )
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["extracted_entities"]["ticket_number"] == "INV-62126"


def test_ticket_upload_extract_supports_multiple_tickets_in_single_file(client: TestClient) -> None:
    headers = _auth_headers(client, "upload5@example.com")

    multi_ticket_text = (
        b"Invoice Number: INV-1001\nMaterial: Dirt\nNet Weight: 20000 lbs\nLoads: 2\n\n"
        b"Ticket # TCK-2002\nMaterial: Sand\nNet Weight: 16000 lbs\nLoads: 1\n"
    )

    response = client.post(
        "/api/tickets/upload-extract?create_tickets=true",
        headers=headers,
        files=[("files", ("multi_ticket_doc.txt", multi_ticket_text, "text/plain"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) >= 2
    ticket_numbers = {item["extracted_entities"].get("ticket_number", "") for item in payload["items"]}
    assert "INV-1001" in ticket_numbers
    assert "TCK-2002" in ticket_numbers

    listed = client.get("/api/tickets", headers=headers)
    assert listed.status_code == 200
    created_numbers = {ticket["ticket_number"] for ticket in listed.json()}
    assert "INV-1001" in created_numbers
    assert "TCK-2002" in created_numbers


def test_ticket_upload_extract_skips_duplicate_ticket_number_when_auto_creating(client: TestClient) -> None:
    headers = _auth_headers(client, "upload6@example.com")

    first = client.post(
        "/api/tickets/upload-extract?create_tickets=true",
        headers=headers,
        files=[
            (
                "files",
                (
                    "dup_1.txt",
                    b"Ticket # DUP-777\nMaterial: Dirt\nNet weight: 12000 lbs",
                    "text/plain",
                ),
            )
        ],
    )
    assert first.status_code == 200
    first_item = first.json()["items"][0]
    assert first_item["created_ticket_id"] is not None
    assert first_item["duplicate_ticket_id"] is None

    second = client.post(
        "/api/tickets/upload-extract?create_tickets=true",
        headers=headers,
        files=[
            (
                "files",
                (
                    "dup_2.txt",
                    b"Ticket # DUP-777\nMaterial: Sand\nNet weight: 14000 lbs",
                    "text/plain",
                ),
            )
        ],
    )
    assert second.status_code == 200
    second_item = second.json()["items"][0]
    assert second_item["created_ticket_id"] is None
    assert second_item["duplicate_ticket_id"] == first_item["created_ticket_id"]

    listed = client.get("/api/tickets", headers=headers)
    assert listed.status_code == 200
    tickets = listed.json()
    assert len(tickets) == 1


def test_ticket_delete_removes_ticket(client: TestClient) -> None:
    headers = _auth_headers(client, "upload7@example.com")

    create_response = client.post(
        "/api/tickets",
        headers=headers,
        json={
            "ticket_number": "DEL-100",
            "material": "Dirt",
            "weight": "20000",
            "status": "draft",
            "notes": "delete test",
        },
    )
    assert create_response.status_code == 201
    ticket_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/tickets/{ticket_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/tickets/{ticket_id}", headers=headers)
    assert get_response.status_code == 404


def test_ticket_create_rejects_canonical_duplicate_ticket_number(client: TestClient) -> None:
    headers = _auth_headers(client, "upload8@example.com")

    first = client.post(
        "/api/tickets",
        headers=headers,
        json={
            "ticket_number": "INV-62126",
            "material": "Dirt",
            "weight": "18000",
            "status": "draft",
            "notes": "first create",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/tickets",
        headers=headers,
        json={
            "ticket_number": "INV 62126",
            "material": "Dirt",
            "weight": "17500",
            "status": "draft",
            "notes": "duplicate create",
        },
    )
    assert second.status_code == 409
    assert "Duplicate ticket number detected" in second.json()["detail"]


def test_ticket_upload_extract_parses_haul_slips_with_comment_load_counts(client: TestClient) -> None:
    headers = _auth_headers(client, "upload9@example.com")

    haul_text = (
        b"P & J Hauling\n16065\nDATE: 6-17-2026\nCONTRACTOR'S NAME: Tirheel Civil\n"
        b"JOB LOCATION: Macedonia RD\nTRUCK #: MJ-11\nMATERIAL SUPPLY: Dirt\n"
        b"Special Hauls or Comments: 7 loads\n\n"
        b"P & J Hauling\n16066\nDATE: 6-17-2026\nCONTRACTOR'S NAME: Tirheel Civil\n"
        b"JOB LOCATION: Macedonia RD\nTRUCK #: MJ-09\nMATERIAL SUPPLY: Dirt\n"
        b"Special Hauls or Comments: 7 loads\n"
    )

    response = client.post(
        "/api/tickets/upload-extract",
        headers=headers,
        files=[("files", ("pj_haul_slips.txt", haul_text, "text/plain"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) >= 2

    ticket_numbers = {item["extracted_entities"].get("ticket_number") for item in payload["items"]}
    assert "16065" in ticket_numbers
    assert "16066" in ticket_numbers

    load_counts = {item["extracted_entities"].get("number_of_loads") for item in payload["items"]}
    assert "7" in load_counts


def test_ticket_upload_extract_parses_mj_notes_lds_load_count(client: TestClient) -> None:
    headers = _auth_headers(client, "upload10@example.com")

    mj_text = (
        b"M&J TWINS HAULING\nDATE: 6/17/26\nTRUCK# MJ-08\nJOB: Harvest District\n"
        b"COMPANY HAULING FOR: Wellons\nSTART TIME: 7:00\nFINISH TIME: 2:00\n"
        b"PRODUCT DIRT\nNOTES: 6 Lds to Dump at 8812 Noble Flare Dr\n"
    )

    response = client.post(
        "/api/tickets/upload-extract",
        headers=headers,
        files=[("files", ("mj_ticket_notes.txt", mj_text, "text/plain"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) >= 1
    item = payload["items"][0]
    assert item["extracted_entities"].get("number_of_loads") == "6"
    assert item["extracted_entities"].get("material", "").lower() == "dirt"