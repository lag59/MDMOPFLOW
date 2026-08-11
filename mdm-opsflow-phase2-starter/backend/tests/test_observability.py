import json
import logging

from app.observability import JsonFormatter, bind_request_context, classify_exception, classify_status, clear_request_context, scrub_value


def test_scrub_value_redacts_sensitive_keys() -> None:
    payload = {
        "password": "super-secret",
        "access_token": "token-value",
        "nested": {"authorization": "Bearer abc", "ok": "value"},
    }

    scrubbed = scrub_value("payload", payload)
    assert scrubbed["password"] == "***REDACTED***"
    assert scrubbed["access_token"] == "***REDACTED***"
    assert scrubbed["nested"]["authorization"] == "***REDACTED***"
    assert scrubbed["nested"]["ok"] == "value"


def test_classify_status_and_exception() -> None:
    assert classify_status(200) == "success"
    assert classify_status(401) == "authentication_error"
    assert classify_status(403) == "authorization_or_business_rule_error"
    assert classify_status(500) == "server_error"

    exc = RuntimeError("boom")
    assert classify_exception(exc) == "internal_error"


def test_json_formatter_includes_request_and_deploy_metadata() -> None:
    bind_request_context(request_id="req-123", method="GET", path="/health")
    logger = logging.getLogger("test.observability")
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        __file__,
        10,
        "request_completed",
        args=(),
        exc_info=None,
        extra={"status_code": 200, "latency_ms": 11.2},
    )

    rendered = JsonFormatter().format(record)
    parsed = json.loads(rendered)

    assert parsed["request_id"] == "req-123"
    assert parsed["method"] == "GET"
    assert parsed["path"] == "/health"
    assert "deployment_id" in parsed
    assert "app_version" in parsed
    assert parsed["status_code"] == 200
    assert parsed["latency_ms"] == 11.2

    clear_request_context()
