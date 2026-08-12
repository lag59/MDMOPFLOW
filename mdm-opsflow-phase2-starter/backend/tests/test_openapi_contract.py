from __future__ import annotations

from collections import Counter

import pytest

from app.main import app
from scripts.generate_openapi_operationid_snapshot import collect_operation_rows


pytestmark = pytest.mark.guardrail


def test_openapi_schema_contains_operations() -> None:
    schema = app.openapi()
    rows = collect_operation_rows(schema)

    assert rows, "OpenAPI schema exposed no HTTP operations"


def test_openapi_operation_ids_are_present_and_unique() -> None:
    schema = app.openapi()
    rows = collect_operation_rows(schema)

    operation_ids = [operation_id for _, _, operation_id in rows]
    missing = [(method, path) for method, path, operation_id in rows if not operation_id]
    duplicates = sorted(
        operation_id
        for operation_id, count in Counter(operation_ids).items()
        if operation_id and count > 1
    )

    assert not missing, f"Operations missing operationId values: {missing}"
    assert not duplicates, f"Duplicate operationId values detected: {duplicates}"


def test_openapi_contract_includes_root_get_operation() -> None:
    schema = app.openapi()
    rows = collect_operation_rows(schema)

    assert ("GET", "/", "root_get") in rows


def test_openapi_contract_ai_assist_operation_ids_are_stable() -> None:
    schema = app.openapi()
    rows = collect_operation_rows(schema)

    assert ("POST", "/api/estimates/{estimate_id}/ai-assist", "estimate_ai_assist") in rows
    assert ("POST", "/estimate/assist/preview", "estimate_ai_assist_preview") in rows
    assert all(operation_id != "estimate_ai_assist_legacy" for _, _, operation_id in rows)
