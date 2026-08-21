from __future__ import annotations

from app.services.document_intake_router import route_ocr_document, should_use_ai_fallback


def test_document_intake_router_extracts_haul_ticket_without_inventing_values() -> None:
    sample = """HAUL TICKET - TEST OCR DOCUMENT
Carolina Haul Services
Ticket No. CH-004821
Date 08/11/2026
Project N. Ridge Commerce Pk Ph 2
Truck T-17
Driver M. SAMPLE
Material EXPORT SOIL
Load 18.6 tons
Origin NRCP PH2
Destination DURHAM FILL SITE B
Time In 10:42
Time Out 11:06"""

    result = route_ocr_document(sample)

    assert result.document_type == "haul_ticket"
    assert result.recommended_route == "Tickets > Hauling"
    assert result.classification_confidence >= 0.90
    assert result.project["name"] == "North Ridge Commerce Park - Phase 2"
    assert result.vendor["name"] == "Carolina Haul Services"
    assert result.vendor["document_number"] == "CH-004821"
    assert result.extracted_fields["load_value"] == 18.6
    assert result.extracted_fields["load_unit"] == "TON"
    assert result.uncertain_fields == []
    assert should_use_ai_fallback(result) is False


def test_document_intake_router_routes_hauling_quote_to_estimator_review() -> None:
    sample = """Hauling / Disposal Quote
Project: N. Ridge Commerce Pk Ph 2
Project Number: NRCP-PH2
Quote Number: HQ-24011
Assumed One-Way Distance: 16 miles
Truck Type Triaxle
Rate $125 per truck-hour
Disposal Fee $8.50 per CY"""

    result = route_ocr_document(sample)

    assert result.document_type == "hauling_disposal_quote"
    assert result.recommended_route == "Estimator > Hauling > Vendor Quotes"
    assert result.project["number"] == "NRCP-PH2"
    assert result.vendor["document_number"] == "HQ-24011"
    assert result.extracted_fields["one_way_distance_miles"] == 16.0
    assert result.extracted_fields["hourly_rate"] == 125.0
    assert result.requires_human_review is False
    assert result.uncertain_fields == []


def test_document_intake_router_routes_general_estimate_to_estimator_review() -> None:
    sample = """Cost Estimate
Project: Riverbend Utility Extension
Estimate Number: EST-2026-014
Bid Form
Work includes earthwork, storm drainage, and water main installation
Cost Breakdown
Estimated Cost $1,245,000
"""

    result = route_ocr_document(sample)

    assert result.document_type == "estimate"
    assert result.recommended_route == "Estimator > Estimates > Review"
    assert result.classification_confidence >= 0.72
    assert result.project["name"] == "Riverbend Utility Extension"
    assert result.requires_human_review is False
    assert should_use_ai_fallback(result) is False


def test_document_intake_router_understands_generic_quote_as_estimate() -> None:
    sample = """Quote
Project: Riverbend Utility Extension
Quote Number: Q-2026-014
Proposal Total: $1,245,000
Work includes earthwork, storm drainage, and water main installation
"""

    result = route_ocr_document(sample)

    assert result.document_type == "generic_quote"
    assert result.recommended_route == "Estimator > Estimates > Review"
    assert result.project["name"] == "Riverbend Utility Extension"
    assert result.vendor["document_number"] == "Q-2026-014"
    assert result.requires_human_review is False


def test_document_intake_router_routes_contract_to_portfolio_review() -> None:
    sample = """Construction Contract
Project: Riverbend Utility Extension
Contract Number: CON-2026-044
Owner-Contractor Agreement
Contract Sum: $4,200,000
Notice to Proceed: 09/01/2026
Substantial Completion: 180 days
Retainage: 5%
"""

    result = route_ocr_document(sample)

    assert result.document_type == "contract"
    assert result.recommended_route == "Projects > Contracts > Review"
    assert result.classification_confidence >= 0.72
    assert result.project["name"] == "Riverbend Utility Extension"
    assert result.vendor["document_number"] == "CON-2026-044"
    assert result.requires_human_review is False