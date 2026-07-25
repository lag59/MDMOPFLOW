from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = ROOT / "docs" / "openapi-operationid-snapshot.md"
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def collect_operation_rows(openapi_schema: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    paths: dict[str, Any] = openapi_schema.get("paths", {})

    for path in sorted(paths):
        path_item: dict[str, Any] = paths[path]
        for method in sorted(path_item):
            if method.lower() not in HTTP_METHODS:
                continue

            operation: dict[str, Any] = path_item.get(method, {})
            operation_id = str(operation.get("operationId", ""))
            rows.append((method.upper(), path, operation_id))

    return rows


def build_snapshot_markdown(rows: list[tuple[str, str, str]]) -> str:
    lines = [
        "# OpenAPI OperationId Snapshot",
        "",
        "Generated from `backend/app/main.py`.",
        "",
        "| Method | Path | Operation ID |",
        "| --- | --- | --- |",
    ]

    if rows:
        for method, path, operation_id in rows:
            lines.append(f"| {method} | `{path}` | `{operation_id}` |")
    else:
        lines.append("| - | - | - |")

    lines.append("")
    return "\n".join(lines)


def generate_snapshot_markdown() -> str:
    schema = app.openapi()
    rows = collect_operation_rows(schema)
    return build_snapshot_markdown(rows)


def write_snapshot(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = generate_snapshot_markdown()
    path.write_text(text, encoding="utf-8")
    return text.count("\n")


def parse_args() -> Path:
    parser = ArgumentParser(description="Generate OpenAPI operationId snapshot markdown")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write markdown snapshot (default: docs/openapi-operationid-snapshot.md)",
    )
    args = parser.parse_args()
    return args.output


def main() -> int:
    output_path = parse_args()
    line_count = write_snapshot(output_path)
    print(f"Wrote OpenAPI snapshot to {output_path} ({line_count} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
