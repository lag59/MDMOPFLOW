from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_fast_guardrails import FAST_TESTS


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"


pytestmark = pytest.mark.guardrail


def test_fast_guardrail_test_paths_exist() -> None:
    missing: list[str] = []

    for relative_path in FAST_TESTS:
        candidate = BACKEND_ROOT / relative_path
        if not candidate.exists():
            missing.append(relative_path)

    assert not missing, f"Missing fast-guardrail tests: {', '.join(sorted(missing))}"


def test_fast_guardrail_manifest_matches_guardrail_marked_tests() -> None:
    guardrail_files = sorted(
        str(path.relative_to(BACKEND_ROOT)).replace("\\", "/")
        for path in (BACKEND_ROOT / "tests").glob("test_*.py")
        if "pytestmark = pytest.mark.guardrail" in path.read_text(encoding="utf-8")
    )

    manifest_files = sorted(FAST_TESTS)

    missing_from_manifest = sorted(set(guardrail_files) - set(manifest_files))
    extra_in_manifest = sorted(set(manifest_files) - set(guardrail_files))

    assert not missing_from_manifest and not extra_in_manifest, (
        "FAST_TESTS manifest drift detected. "
        f"Missing from manifest: {missing_from_manifest}. "
        f"Extra in manifest: {extra_in_manifest}."
    )


def test_fast_guardrail_manifest_has_no_duplicates() -> None:
    assert len(FAST_TESTS) == len(set(FAST_TESTS)), "FAST_TESTS contains duplicate entries"


def test_fast_guardrail_manifest_is_sorted_for_stable_diffs() -> None:
    assert FAST_TESTS == sorted(FAST_TESTS), "FAST_TESTS must stay alphabetically sorted"
