from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PR_TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"


pytestmark = pytest.mark.guardrail


def test_pr_template_exists() -> None:
    assert PR_TEMPLATE.exists(), "Missing .github/PULL_REQUEST_TEMPLATE.md"


def test_pr_template_contains_validation_baseline() -> None:
    source = PR_TEMPLATE.read_text(encoding="utf-8")

    required_snippets = [
        "run_fast_guardrails.py",
        "python.exe -m pytest -q",
        "Fast guardrails: `91 passed, 15 deselected`",
        "Full backend suite: `106 passed`",
        "Warnings: none",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in source]
    assert not missing, "PR template missing required validation guidance: " + ", ".join(missing)