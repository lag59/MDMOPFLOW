from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"


pytestmark = pytest.mark.guardrail


def test_readme_exists() -> None:
    assert README.exists(), "Missing README.md"


def test_readme_contains_guardrail_commands_and_triage_notes() -> None:
    source = README.read_text(encoding="utf-8")

    required_snippets = [
        "backend/scripts/run_fast_guardrails.py",
        "git config core.hooksPath .githooks",
        "backend-fast-guardrails-output",
        "Guardrail Failure Playbook",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in source]
    assert not missing, "README guardrail docs missing: " + ", ".join(missing)