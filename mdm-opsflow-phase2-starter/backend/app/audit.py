from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {k: _to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())
    return str(value)


def _to_json(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(_to_jsonable(value), sort_keys=True)


def get_request_id(request: Request | None) -> str | None:
    if request is None:
        return None
    state_request_id = getattr(request.state, "request_id", None)
    if state_request_id:
        return str(state_request_id)
    header_request_id = request.headers.get("X-Request-ID")
    return header_request_id or None


def add_audit_log(
    db: Session,
    *,
    actor_user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    tenant_id: str | None,
    request_id: str | None,
    details: str = "",
    before: Any = None,
    after: Any = None,
) -> AuditLog:
    row = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=entity_type,
        resource_id=entity_id,
        details=details,
        created_by=actor_user_id,
        request_id=request_id,
        before_values_json=_to_json(before),
        after_values_json=_to_json(after),
    )
    db.add(row)
    return row
