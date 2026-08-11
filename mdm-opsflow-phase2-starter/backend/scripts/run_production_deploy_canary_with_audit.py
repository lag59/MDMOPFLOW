from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from verify_production_deploy_canary import DEFAULT_BASE_URL, DEFAULT_PASSWORD, run_canary


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "backend" / "artifacts"
AUDIT_FILE = AUDIT_DIR / "production-deploy-canary.jsonl"


def _append_audit_log(record: dict[str, object]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def main() -> int:
    base_url = os.getenv("OPSFLOW_CANARY_BASE_URL") or DEFAULT_BASE_URL
    password = os.getenv("OPSFLOW_CANARY_PASSWORD") or DEFAULT_PASSWORD

    started_at = datetime.now(timezone.utc)
    exit_code, results = run_canary(base_url=base_url, password=password)
    finished_at = datetime.now(timezone.utc)

    audit_record: dict[str, object] = {
        "timestamp_utc": finished_at.isoformat(),
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "exit_code": exit_code,
        "base_url": results.get("base_url", base_url),
        "email": results.get("email"),
        "register": results.get("register"),
        "onboarding": results.get("onboarding"),
        "project_create": results.get("project_create"),
        "assist": results.get("assist"),
        "tickets_list": results.get("tickets_list"),
    }
    _append_audit_log(audit_record)

    print(json.dumps(results, indent=2))
    print(f"Audit log updated: {AUDIT_FILE}")

    if exit_code == 0:
        print("Deploy canary passed: /api/daily-field-reports/assist and /api/tickets are healthy.")
    else:
        print("Deploy canary failed. See JSON output and audit log for details.")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
