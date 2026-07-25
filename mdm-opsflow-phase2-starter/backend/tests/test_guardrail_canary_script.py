from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CANARY_SCRIPT = ROOT / "backend" / "scripts" / "verify_streamlit_guardrail_canary.py"


pytestmark = pytest.mark.guardrail


def test_guardrail_canary_script_exists() -> None:
    assert CANARY_SCRIPT.exists(), "Missing Streamlit guardrail canary script"


def test_guardrail_canary_script_restores_streamlit_file_and_expects_failure() -> None:
    source = CANARY_SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "CORRUPTION_FRAGMENT =",
        "tests/test_streamlit_script_syntax.py",
        "finally:",
        "STREAMLIT_APP.write_text(original_source, encoding=\"utf-8\")",
        "completed.returncode == 0",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in source]
    assert not missing, "Canary script contract drift detected: " + ", ".join(missing)
