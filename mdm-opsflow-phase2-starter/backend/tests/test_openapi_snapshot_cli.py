from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "generate_openapi_operationid_snapshot.py"


pytestmark = pytest.mark.guardrail


def test_openapi_snapshot_generator_script_exists() -> None:
    assert SCRIPT_PATH.exists(), "Missing OpenAPI snapshot generator script"


def test_openapi_snapshot_generator_cli_writes_output(tmp_path: Path) -> None:
    output_file = tmp_path / "openapi-operationid-snapshot.md"

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output", str(output_file)],
        cwd=BACKEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert output_file.exists(), "Snapshot generator did not write output file"
    assert "Wrote OpenAPI snapshot to" in completed.stdout

    content = output_file.read_text(encoding="utf-8")
    assert "# OpenAPI OperationId Snapshot" in content
    assert "| Method | Path | Operation ID |" in content
