from __future__ import annotations

from app.services.ocr_extraction_service import _build_field_level_discrepancies


def test_field_level_discrepancies_emit_expected_kinds() -> None:
    payload = {
        "quantities": [
            {
                "value": "100",
                "unit": "CY",
                "source_document_type": "bid_schedule",
                "original_source_text": "100 CY export",
                "authority_level": "document",
                "confidence": 0.8,
            },
            {
                "value": "120",
                "unit": "CY",
                "source_document_type": "addendum",
                "original_source_text": "revised to 120 CY",
                "authority_level": "addendum",
                "confidence": 0.7,
            },
        ],
        "haul_costs": [
            {
                "value": "16",
                "unit": "miles",
                "source_document_type": "vendor_material_quote",
                "original_source_text": "16 miles one-way",
                "authority_level": "quote",
                "confidence": 0.9,
            },
            {
                "value": "18",
                "unit": "miles",
                "source_document_type": "addendum",
                "original_source_text": "18 miles one-way",
                "authority_level": "addendum",
                "confidence": 0.5,
            },
        ],
        "allowances": [
            {
                "value": "200",
                "unit": "CY",
                "source_document_type": "geotechnical_report",
                "original_source_text": "undercut allowance 200 CY",
                "authority_level": "geotech",
                "confidence": 0.8,
            },
            {
                "value": "150",
                "unit": "CY",
                "source_document_type": "bid_schedule",
                "original_source_text": "allowance 150 CY",
                "authority_level": "document",
                "confidence": 0.7,
            },
        ],
    }

    discrepancies = _build_field_level_discrepancies(payload)
    kinds = {entry["kind"] for entry in discrepancies}

    assert "quantity_conflict" in kinds
    assert "haul_cost_conflict" in kinds
    assert "allowance_conflict" in kinds


def test_field_level_discrepancies_apply_authority_precedence() -> None:
    payload = {
        "quantities": [
            {
                "value": "100",
                "unit": "CY",
                "source_document_type": "bid_schedule",
                "original_source_text": "100 CY",
                "authority_level": "document",
                "confidence": 0.95,
            },
            {
                "value": "120",
                "unit": "CY",
                "source_document_type": "addendum",
                "original_source_text": "revised to 120 CY",
                "authority_level": "addendum",
                "confidence": 0.55,
            },
        ]
    }

    discrepancies = _build_field_level_discrepancies(payload)
    quantity_discrepancy = next(item for item in discrepancies if item["kind"] == "quantity_conflict")
    recommended = quantity_discrepancy["recommended"]

    assert float(recommended["value"]) == 120.0
    assert recommended["authority_level"] == "addendum"


def test_field_level_discrepancies_skip_when_values_do_not_conflict() -> None:
    payload = {
        "quantities": [
            {
                "value": "100",
                "unit": "CY",
                "source_document_type": "bid_schedule",
                "authority_level": "document",
                "confidence": 0.9,
            },
            {
                "value": "100.0000",
                "unit": "CY",
                "source_document_type": "addendum",
                "authority_level": "addendum",
                "confidence": 0.9,
            },
        ]
    }

    discrepancies = _build_field_level_discrepancies(payload)
    assert discrepancies == []
