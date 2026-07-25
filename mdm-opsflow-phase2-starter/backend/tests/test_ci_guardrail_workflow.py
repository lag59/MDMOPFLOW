from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "backend-ci.yml"


pytestmark = pytest.mark.guardrail


def test_backend_ci_workflow_exists() -> None:
    assert WORKFLOW.exists(), "Missing backend CI workflow file"


def test_backend_ci_runs_fast_guardrails() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "backend/scripts/run_fast_guardrails.py" in source
    assert "backend-fast-guardrails-output" in source
    assert "actions/upload-artifact@v4" in source


def test_backend_ci_full_test_phase_excludes_guardrail_marker() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert 'pytest -q -m "not guardrail"' in source


def test_backend_ci_fast_guardrail_logging_and_artifact_wiring() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "set -o pipefail" in source
    assert "tee backend-fast-guardrails.log" in source
    assert "if: always()" in source
    assert "path: backend-fast-guardrails.log" in source


def test_backend_ci_path_filters_include_streamlit_and_workflow_files() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "on:" in source
    assert "push:" in source
    assert "pull_request:" in source
    assert "- streamlit_app.py" in source
    assert "- .github/workflows/backend-ci.yml" in source


def test_backend_ci_path_filters_include_backend_and_openapi_snapshot() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "- backend/**" in source
    assert "- docs/openapi-operationid-snapshot.md" in source


def test_backend_ci_supports_manual_dispatch_and_pinned_python() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in source
    assert "actions/setup-python@v5" in source
    assert 'python-version: "3.12"' in source