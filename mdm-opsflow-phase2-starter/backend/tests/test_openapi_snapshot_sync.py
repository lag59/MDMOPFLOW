from __future__ import annotations

from pathlib import Path

import pytest

from scripts.generate_openapi_operationid_snapshot import generate_snapshot_markdown


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / "docs" / "openapi-operationid-snapshot.md"


pytestmark = pytest.mark.guardrail


def test_openapi_snapshot_file_exists() -> None:
    assert SNAPSHOT_PATH.exists(), "Missing docs/openapi-operationid-snapshot.md"


def test_openapi_snapshot_matches_current_schema() -> None:
    expected = generate_snapshot_markdown()
    actual = SNAPSHOT_PATH.read_text(encoding="utf-8")

    assert actual == expected, (
        "OpenAPI snapshot drift detected. Regenerate with: "
        "python backend/scripts/generate_openapi_operationid_snapshot.py"
    )
