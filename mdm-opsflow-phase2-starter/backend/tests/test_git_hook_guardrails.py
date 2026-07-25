from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PRE_COMMIT_HOOK = ROOT / ".githooks" / "pre-commit"


pytestmark = pytest.mark.guardrail


def test_pre_commit_hook_exists() -> None:
    assert PRE_COMMIT_HOOK.exists(), "Missing .githooks/pre-commit hook"


def test_pre_commit_hook_runs_fast_guardrails() -> None:
    source = PRE_COMMIT_HOOK.read_text(encoding="utf-8")

    assert "backend/scripts/run_fast_guardrails.py" in source
    assert "set -eu" in source


def test_pre_commit_hook_uses_repo_root_and_python_fallback_chain() -> None:
    source = PRE_COMMIT_HOOK.read_text(encoding="utf-8")

    assert source.startswith("#!/usr/bin/env sh\n")
    assert "git rev-parse --show-toplevel" in source
    assert 'cd "$repo_root"' in source
    assert "./.venv311/Scripts/python.exe" in source
    assert "./.venv/Scripts/python.exe" in source
    assert "python \"./backend/scripts/run_fast_guardrails.py\"" in source