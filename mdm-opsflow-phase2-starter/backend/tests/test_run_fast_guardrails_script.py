from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_fast_guardrails


pytestmark = pytest.mark.guardrail


def test_run_fast_guardrails_main_invokes_pytest_guardrail_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> Completed:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        return Completed()

    monkeypatch.setattr(run_fast_guardrails.subprocess, "run", fake_run)

    result = run_fast_guardrails.main()

    assert result == 0
    assert captured["command"] == [
        run_fast_guardrails.sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        "guardrail",
    ]
    assert captured["cwd"] == run_fast_guardrails.BACKEND_ROOT
    assert captured["check"] is False


def test_run_fast_guardrails_main_propagates_pytest_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    class Completed:
        returncode = 7

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> Completed:
        return Completed()

    monkeypatch.setattr(run_fast_guardrails.subprocess, "run", fake_run)

    assert run_fast_guardrails.main() == 7