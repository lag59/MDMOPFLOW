"""Manual extraction test - run via docker compose exec backend pytest tests/test_extraction_manual.py -s"""
from __future__ import annotations

import os

import pytest

PDF_PATH = "/tmp/invoice1508.pdf"


@pytest.mark.skipif(not os.path.exists(PDF_PATH), reason="PDF not copied into container")
def test_invoice_1508_extraction() -> None:
    from app.services.intake_processing import process_intake_upload
    from app.services.ticket_extractor import extract_ticket_candidates

    with open(PDF_PATH, "rb") as f:
        payload = f.read()

    result = process_intake_upload(
        tenant_id="test",
        original_filename="Tickets for invoice 1508.pdf",
        mime_type="application/pdf",
        payload=payload,
    )

    print("\n=== OCR TEXT (first 1400 chars) ===")
    print(result.extracted_text[:1400])

    candidates = extract_ticket_candidates(
        result.extracted_text,
        original_filename="Tickets for invoice 1508.pdf",
    )

    print(f"\n=== {len(candidates)} CANDIDATE(S) ===")
    for i, c in enumerate(candidates):
        print(f"\n-- Candidate {i + 1} --")
        for k, v in c.items():
            print(f"  {k}: {v}")

    assert len(candidates) >= 1

    # Across the candidates, we expect to find at least:
    # - a load count
    # - a material (Dirt)
    # - a truck identifier
    all_loads = [c.get("number_of_loads", "") for c in candidates if c.get("number_of_loads")]
    all_materials = [c.get("material", "") for c in candidates if c.get("material")]
    all_trucks = [c.get("truck", "") for c in candidates if c.get("truck")]

    print(f"\nLoads found: {all_loads}")
    print(f"Materials found: {all_materials}")
    print(f"Trucks found: {all_trucks}")

    assert any(m.lower() in ("dirt", "stone", "sand") for m in all_materials), f"No material found; got {all_materials}"
