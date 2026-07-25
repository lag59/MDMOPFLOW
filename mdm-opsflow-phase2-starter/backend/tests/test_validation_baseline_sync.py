from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
PR_TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"


pytestmark = pytest.mark.guardrail


def test_validation_baseline_strings_match_between_readme_and_pr_template() -> None:
    readme = README.read_text(encoding="utf-8")
    pr_template = PR_TEMPLATE.read_text(encoding="utf-8")

    baseline_strings = [
        "Fast guardrails: `91 passed, 15 deselected`",
        "Full backend suite: `106 passed`",
        "Warnings: none",
    ]

    missing_from_readme = [text for text in baseline_strings if text not in readme]
    missing_from_pr_template = [text for text in baseline_strings if text not in pr_template]

    assert not missing_from_readme and not missing_from_pr_template, (
        "Validation baseline drift detected. "
        f"Missing from README: {missing_from_readme}. "
        f"Missing from PR template: {missing_from_pr_template}."
    )


def test_validation_command_snippets_exist_in_readme_and_pr_template() -> None:
    readme = README.read_text(encoding="utf-8")
    pr_template = PR_TEMPLATE.read_text(encoding="utf-8")

    command_snippets = [
        ".\\backend\\scripts\\run_fast_guardrails.py",
        "python.exe -m pytest -q",
    ]

    missing_from_readme = [text for text in command_snippets if text not in readme]
    missing_from_pr_template = [text for text in command_snippets if text not in pr_template]

    assert not missing_from_readme and not missing_from_pr_template, (
        "Validation command drift detected. "
        f"Missing from README: {missing_from_readme}. "
        f"Missing from PR template: {missing_from_pr_template}."
    )