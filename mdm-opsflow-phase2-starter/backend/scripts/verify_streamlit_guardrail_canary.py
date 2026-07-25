from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
STREAMLIT_APP = ROOT / "streamlit_app.py"

CANONICAL_IMPORT = "import streamlit as st  # pyright: ignore[reportMissingImports]"
CORRUPTION_FRAGMENT = "n\n\nimport stream\n"
TARGET_TEST = "tests/test_streamlit_script_syntax.py"


def _run_target_guardrail_test() -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        "guardrail",
        TARGET_TEST,
    ]
    return subprocess.run(command, cwd=BACKEND_ROOT, check=False, text=True)


def main() -> int:
    original_source = STREAMLIT_APP.read_text(encoding="utf-8")

    if CANONICAL_IMPORT not in original_source:
        print("Cannot run canary: canonical Streamlit import line was not found.")
        return 2

    corrupted_source = original_source.replace(
        CANONICAL_IMPORT,
        f"{CORRUPTION_FRAGMENT}{CANONICAL_IMPORT}",
        1,
    )

    if corrupted_source == original_source:
        print("Cannot run canary: failed to inject corruption fragment.")
        return 2

    try:
        STREAMLIT_APP.write_text(corrupted_source, encoding="utf-8")
        completed = _run_target_guardrail_test()
    finally:
        STREAMLIT_APP.write_text(original_source, encoding="utf-8")

    if completed.returncode == 0:
        print("Guardrail canary failed: corruption did not trigger a guardrail failure.")
        return 1

    print("Guardrail canary passed: corruption was detected and streamlit_app.py was restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
