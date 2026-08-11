from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)
_PATH: ContextVar[str | None] = ContextVar("path", default=None)
_METHOD: ContextVar[str | None] = ContextVar("method", default=None)
_USER_ID: ContextVar[str | None] = ContextVar("user_id", default=None)
_TENANT_ID: ContextVar[str | None] = ContextVar("tenant_id", default=None)

REDACTED = "***REDACTED***"
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "token",
    "secret",
    "authorization",
    "database_url",
    "api_key",
    "cookie",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "environment": settings.ENVIRONMENT,
            "app_version": settings.APP_VERSION,
            "deployment_id": settings.DEPLOYMENT_ID,
            "request_id": _REQUEST_ID.get(),
            "method": _METHOD.get(),
            "path": _PATH.get(),
            "user_id": _USER_ID.get(),
            "tenant_id": _TENANT_ID.get(),
        }

        standard = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }

        for key, value in record.__dict__.items():
            if key in standard:
                continue
            payload[key] = scrub_value(key, value)

        if record.exc_info:
            exc_type = record.exc_info[0]
            payload["error_type"] = exc_type.__name__ if exc_type else "Exception"
            payload["error_classification"] = classify_exception(record.exc_info[1])

        return json.dumps(payload, sort_keys=True, default=str)


def scrub_value(key: str, value: Any) -> Any:
    lower_key = key.lower()
    if any(fragment in lower_key for fragment in SENSITIVE_KEY_FRAGMENTS):
        return REDACTED

    if isinstance(value, dict):
        return {k: scrub_value(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [scrub_value(key, item) for item in value]
    if isinstance(value, str) and len(value) > 4096:
        return value[:4096] + "..."
    return value


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)

    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


def bind_request_context(*, request_id: str, method: str, path: str) -> None:
    _REQUEST_ID.set(request_id)
    _METHOD.set(method)
    _PATH.set(path)


def bind_identity(*, user_id: str | None = None, tenant_id: str | None = None) -> None:
    if user_id is not None:
        _USER_ID.set(user_id)
    if tenant_id is not None:
        _TENANT_ID.set(tenant_id)


def clear_request_context() -> None:
    _REQUEST_ID.set(None)
    _METHOD.set(None)
    _PATH.set(None)
    _USER_ID.set(None)
    _TENANT_ID.set(None)


def get_request_id() -> str | None:
    return _REQUEST_ID.get()


def classify_exception(exc: BaseException | None) -> str:
    if exc is None:
        return "unknown"
    if isinstance(exc, HTTPException):
        return classify_status(exc.status_code)
    if isinstance(exc, SQLAlchemyError):
        return "database_error"
    return "internal_error"


def classify_status(status_code: int) -> str:
    if status_code == 401:
        return "authentication_error"
    if status_code in {403, 404, 409}:
        return "authorization_or_business_rule_error"
    if status_code >= 500:
        return "server_error"
    if status_code >= 400:
        return "client_error"
    return "success"
