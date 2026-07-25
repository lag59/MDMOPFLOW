from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = ROOT / "backend" / "pytest.ini"


pytestmark = pytest.mark.guardrail


def test_pytest_ini_exists() -> None:
    assert PYTEST_INI.exists(), "Missing backend/pytest.ini"


def test_pytest_ini_defines_guardrail_marker() -> None:
    source = PYTEST_INI.read_text(encoding="utf-8")

    assert "markers" in source
    assert "guardrail:" in source
    assert "fast contract and integrity checks" in source