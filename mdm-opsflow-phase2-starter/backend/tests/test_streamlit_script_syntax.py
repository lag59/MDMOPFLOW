from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
STREAMLIT_APP = ROOT / "streamlit_app.py"

EXPECTED_HEADER_PREFIX = [
    "from __future__ import annotations",
    "",
    "# pyright: reportUnknownMemberType=false",
    "",
    "from typing import Any, cast",
    "from urllib.error import HTTPError, URLError",
    "from urllib.request import Request, urlopen",
    "",
    "import streamlit as st  # pyright: ignore[reportMissingImports]",
]


def _known_corruption_fingerprints(source: str) -> list[str]:
    findings: set[str] = set()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        for line in source.splitlines():
            normalized = line.strip()
            if normalized == "n":
                findings.add("n")
            # Catch spacing/comment variants like "import    stream" or
            # "import stream  # TODO" while avoiding false positives for
            # the valid "import streamlit as st" canonical line.
            if _is_stream_fragment_import_line(normalized):
                findings.add("import stream")
    else:
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name) and node.value.id == "n":
                findings.add("n")
            if isinstance(node, ast.Import) and any(alias.name == "stream" for alias in node.names):
                findings.add("import stream")
            if isinstance(node, ast.ImportFrom) and node.module == "stream":
                findings.add("import stream")

    return sorted(findings)


def _is_import_stream_line(normalized_line: str) -> bool:
    return bool(
        re.fullmatch(r"import\s+stream(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?(?:\s*#.*)?", normalized_line)
    )


def _is_from_stream_import_line(normalized_line: str) -> bool:
    return bool(
        re.fullmatch(
            r"from\s+stream\s+import\s+[A-Za-z_*][A-Za-z0-9_,\s]*(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?(?:\s*#.*)?",
            normalized_line,
        )
    )


def _is_stream_fragment_import_line(normalized_line: str) -> bool:
    return _is_import_stream_line(normalized_line) or _is_from_stream_import_line(normalized_line)


def _contains_known_corruption_sequence(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        normalized_lines = [line.strip() for line in source.splitlines()]
        for index, line in enumerate(normalized_lines):
            if line != "n":
                continue
            for later_line in normalized_lines[index + 1 :]:
                if _is_stream_fragment_import_line(later_line):
                    return True
        return False

    seen_n = False
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name) and node.value.id == "n":
            seen_n = True
            continue

        is_stream_import = False
        if isinstance(node, ast.Import):
            is_stream_import = any(alias.name == "stream" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            is_stream_import = node.module == "stream"

        if seen_n and is_stream_import:
            return True

    return False


def _prefix_before_canonical_streamlit_import(source: str) -> str:
    lines = source.splitlines()
    canonical = "import streamlit as st  # pyright: ignore[reportMissingImports]"
    import_index = next(i for i, line in enumerate(lines) if line == canonical)
    return "\n".join(lines[:import_index])


pytestmark = pytest.mark.guardrail


def test_streamlit_app_starts_with_future_import() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    assert source.startswith("from __future__ import annotations\n")


def test_streamlit_app_has_single_first_future_annotations_import() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(STREAMLIT_APP))

    future_import_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
    ]

    assert len(future_import_nodes) == 1, "Expected exactly one future annotations import"
    assert tree.body, "Expected non-empty module body"
    assert future_import_nodes[0] is tree.body[0], (
        "Future annotations import must remain the first top-level statement"
    )


def test_streamlit_app_compiles() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    compile(source, str(STREAMLIT_APP), "exec")


def test_streamlit_app_has_no_bom_or_nul_bytes() -> None:
    payload = STREAMLIT_APP.read_bytes()

    assert not payload.startswith(b"\xef\xbb\xbf"), "streamlit_app.py must not contain a UTF-8 BOM"
    assert b"\x00" not in payload, "streamlit_app.py must not contain NUL bytes"


def test_streamlit_import_line_present() -> None:
    lines = STREAMLIT_APP.read_text(encoding="utf-8").splitlines()
    canonical = "import streamlit as st  # pyright: ignore[reportMissingImports]"

    matching = [line for line in lines if line == canonical]
    assert len(matching) == 1, "Expected exactly one canonical Streamlit import line"

    partials = [
        line
        for line in lines
        if _is_stream_fragment_import_line(line.strip()) and line != canonical
    ]
    assert not partials, "Unexpected partial stream import line(s): " + ", ".join(repr(line) for line in partials)


def test_streamlit_app_has_exactly_one_canonical_streamlit_import_at_ast_level() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(STREAMLIT_APP))

    streamlit_import_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.Import)
        and any(alias.name == "streamlit" and alias.asname == "st" for alias in node.names)
    ]
    from_streamlit_import_nodes = [
        node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == "streamlit"
    ]

    assert len(streamlit_import_nodes) == 1, "Expected exactly one top-level 'import streamlit as st' statement"
    assert not from_streamlit_import_nodes, "Did not expect any 'from streamlit import ...' statements"


def test_streamlit_header_has_no_stray_tokens_before_streamlit_import() -> None:
    lines = STREAMLIT_APP.read_text(encoding="utf-8").splitlines()
    streamlit_import_index = next(
        idx for idx, line in enumerate(lines) if line.startswith("import streamlit as st")
    )

    allowed_prefixes = (
        "from __future__ import annotations",
        "# pyright:",
        "from typing ",
        "from urllib.error ",
        "from urllib.request ",
    )

    unexpected_lines = [
        line
        for line in lines[:streamlit_import_index]
        if line.strip() and not line.startswith(allowed_prefixes)
    ]

    assert not unexpected_lines, (
        "Unexpected line(s) before Streamlit import: "
        + ", ".join(repr(line) for line in unexpected_lines)
    )


def test_streamlit_app_has_no_top_level_bare_name_statements() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(STREAMLIT_APP))

    bare_names = [
        node
        for node in tree.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name)
    ]

    assert not bare_names, (
        "Unexpected top-level bare name statement(s) in streamlit_app.py at line(s): "
        + ", ".join(str(node.lineno) for node in bare_names)
    )


def test_streamlit_app_has_no_top_level_import_stream_statements() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(STREAMLIT_APP))

    bad_import_lines: list[int] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "stream":
                    bad_import_lines.append(node.lineno)
        if isinstance(node, ast.ImportFrom) and node.module == "stream":
            bad_import_lines.append(node.lineno)

    assert not bad_import_lines, (
        "Unexpected top-level import of module 'stream' in streamlit_app.py at line(s): "
        + ", ".join(str(line) for line in sorted(set(bad_import_lines)))
    )


def test_streamlit_import_appears_before_any_st_usage() -> None:
    lines = STREAMLIT_APP.read_text(encoding="utf-8").splitlines()
    canonical = "import streamlit as st  # pyright: ignore[reportMissingImports]"

    import_index = next(i for i, line in enumerate(lines) if line == canonical)
    first_st_usage_index = next(
        i for i, line in enumerate(lines) if "st." in line and not line.strip().startswith("import ")
    )

    assert import_index < first_st_usage_index, (
        "Streamlit import must appear before first st. usage "
        f"(import line {import_index + 1}, first usage line {first_st_usage_index + 1})"
    )


def test_streamlit_header_prefix_matches_expected() -> None:
    lines = STREAMLIT_APP.read_text(encoding="utf-8").splitlines()
    assert lines[: len(EXPECTED_HEADER_PREFIX)] == EXPECTED_HEADER_PREFIX


def test_streamlit_header_prefix_is_ascii_only() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    prefix = _prefix_before_canonical_streamlit_import(source)
    assert prefix.isascii(), "Header prefix before canonical Streamlit import must remain ASCII-only"


def test_streamlit_header_prefix_has_no_unexpected_control_characters() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    prefix = _prefix_before_canonical_streamlit_import(source)

    # Allow normal whitespace controls but reject all other C0 control chars.
    disallowed = [
        ch for ch in prefix if ord(ch) < 32 and ch not in {"\n", "\r", "\t"}
    ]
    assert not disallowed, (
        "Header prefix before canonical Streamlit import contains unexpected control characters"
    )


def test_streamlit_app_does_not_contain_known_corruption_fingerprint_lines() -> None:
    present = _known_corruption_fingerprints(STREAMLIT_APP.read_text(encoding="utf-8"))

    assert not present, (
        "Detected known corruption fingerprint line(s) in streamlit_app.py: "
        + ", ".join(repr(line) for line in present)
    )


def test_streamlit_app_does_not_contain_known_corruption_sequence() -> None:
    source = STREAMLIT_APP.read_text(encoding="utf-8")
    assert not _contains_known_corruption_sequence(_prefix_before_canonical_streamlit_import(source))


def test_known_corruption_fingerprint_detector_flags_sample_fragment() -> None:
    sample = "from __future__ import annotations\n\n n\n\nimport stream\n"
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream", "n"]


def test_known_corruption_fingerprint_detector_flags_import_stream_spacing_variant() -> None:
    sample = "import    stream\n"
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream"]


def test_known_corruption_fingerprint_detector_flags_import_stream_comment_variant() -> None:
    sample = "import stream   # broken fragment\n"
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream"]


def test_known_corruption_fingerprint_detector_flags_import_stream_alias_variant() -> None:
    sample = "import stream as stream_mod\n"
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream"]


def test_known_corruption_fingerprint_detector_flags_from_stream_import_variant() -> None:
    sample = "from stream import value\n"
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream"]


def test_known_corruption_fingerprint_detector_flags_from_stream_import_alias_variant() -> None:
    sample = "from stream import value as stream_value\n"
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream"]


def test_known_corruption_fingerprint_detector_flags_windows_crlf_fragment() -> None:
    sample = "from __future__ import annotations\r\n\r\n n\r\n\r\nimport stream\r\n"
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream", "n"]


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        ("import stream\n", ["import stream"]),
        ("import\tstream\n", ["import stream"]),
        ("import stream; x = 1\n", ["import stream"]),
        ("from stream import value\n", ["import stream"]),
        ("from stream import *\n", ["import stream"]),
        ("from stream import value; x = 1\n", ["import stream"]),
        ("from stream import value  # bad fragment\n", ["import stream"]),
        ("import streamlit as st\n", []),
        ("import streaming\n", []),
        ("from streaming import value\n", []),
        ("n\n", ["n"]),
    ],
)
def test_known_corruption_fingerprint_detector_matrix(sample: str, expected: list[str]) -> None:
    assert _known_corruption_fingerprints(sample) == expected


def test_known_corruption_sequence_detector_flags_sample_fragment() -> None:
    sample = "from __future__ import annotations\n\n n\n\nimport stream\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_flags_comment_variant() -> None:
    sample = "n\nimport stream  # broken fragment\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_flags_alias_variant() -> None:
    sample = "n\nimport stream as stream_mod\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_flags_from_stream_import_variant() -> None:
    sample = "n\nfrom stream import value\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_flags_with_intervening_comment_and_blank_line() -> None:
    sample = "n\n\n# corrupted fragment follows\nfrom stream import value\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_fallback_flags_from_stream_alias_variant() -> None:
    sample = "from __future__ import annotations\n\n n\n\nfrom stream import value as stream_value\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_flags_same_line_semicolon_variant() -> None:
    sample = "n; import stream\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_flags_same_line_semicolon_from_import_variant() -> None:
    sample = "n; from stream import value\n"
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_flags_windows_crlf_fragment() -> None:
    sample = "from __future__ import annotations\r\n\r\n n\r\n\r\nimport stream\r\n"
    assert _contains_known_corruption_sequence(sample)


@pytest.mark.parametrize(
    "sample",
    [
        "from __future__ import annotations\r\n\r\n\tn\r\n\r\nimport stream\n",
        "from __future__ import annotations\n\n n\r\n\nfrom stream import value\r\n",
        "from __future__ import annotations\r\n\r\n n\n\nimport\tstream\r\n",
    ],
)
def test_known_corruption_fingerprint_detector_flags_mixed_eol_whitespace_variants(sample: str) -> None:
    present = _known_corruption_fingerprints(sample)
    assert present == ["import stream", "n"]


@pytest.mark.parametrize(
    "sample",
    [
        "from __future__ import annotations\r\n\r\n\tn\r\n\r\nimport stream\n",
        "from __future__ import annotations\n\n n\r\n\nfrom stream import value\r\n",
        "from __future__ import annotations\r\n\r\n n\n\nimport\tstream\r\n",
    ],
)
def test_known_corruption_sequence_detector_flags_mixed_eol_whitespace_variants(sample: str) -> None:
    assert _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_detector_ignores_non_matching_content() -> None:
    sample = "from __future__ import annotations\n\nimport streamlit as st\n"
    assert not _contains_known_corruption_sequence(sample)


def test_known_corruption_sequence_file_check_scope_ignores_late_non_header_lines() -> None:
    sample = (
        "from __future__ import annotations\n"
        "\n"
        "import streamlit as st  # pyright: ignore[reportMissingImports]\n"
        "\n"
        "# Later content should not affect header corruption check\n"
        "n\n"
        "import stream\n"
    )
    assert not _contains_known_corruption_sequence(_prefix_before_canonical_streamlit_import(sample))


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("import stream", True),
        ("import\tstream", True),
        ("import stream as stream_mod", True),
        ("import stream  # fragment", True),
        ("from stream import value", True),
        ("from stream import value as stream_value", True),
        ("from stream import *", True),
        ("import streamlit as st", False),
        ("import streaming", False),
        ("from streaming import value", False),
        ("from streamlit import value", False),
    ],
)
def test_stream_fragment_import_line_matcher(line: str, expected: bool) -> None:
    assert _is_stream_fragment_import_line(line) is expected
