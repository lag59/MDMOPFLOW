from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"

FAST_TESTS = [
    "tests/test_ci_guardrail_workflow.py",
    "tests/test_fast_guardrail_manifest.py",
    "tests/test_git_hook_guardrails.py",
    "tests/test_guardrail_canary_script.py",
    "tests/test_guardrail_docs_sync.py",
    "tests/test_openapi_contract.py",
    "tests/test_openapi_snapshot_cli.py",
    "tests/test_openapi_snapshot_sync.py",
    "tests/test_pr_template_guardrails.py",
    "tests/test_pytest_guardrail_marker.py",
    "tests/test_run_fast_guardrails_script.py",
    "tests/test_streamlit_script_syntax.py",
    "tests/test_validation_baseline_sync.py",
]


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", "-m", "guardrail"]
    completed = subprocess.run(command, cwd=BACKEND_ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
