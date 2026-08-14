"""
Tests for HIMP security-event logging.
"""

import logging

from himp.lib.security_events import (
    ACCOUNT_LOCKED,
    AUTHORIZATION_DENIED,
    LOGIN_FAILURE,
    LOGIN_SUCCESS,
    LOGOUT,
    PASSWORD_CHANGED,
    PASSWORD_RESET,
    SESSION_REVOKED,
    log_security_event,
)


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def make_capture_handler():
    logger = logging.getLogger("himp.security")
    handler = CaptureHandler()

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger, handler


def remove_capture_handler(logger, handler):
    logger.removeHandler(handler)


def test_security_event_logs_event_and_username():
    logger, handler = make_capture_handler()

    try:
        log_security_event(
            LOGIN_SUCCESS,
            username="admin",
            outcome="success",
        )
    finally:
        remove_capture_handler(logger, handler)

    assert len(handler.records) == 1

    record = handler.records[0]

    assert record.event == LOGIN_SUCCESS
    assert record.username == "admin"
    assert record.outcome == "success"


def test_security_event_supports_reason_and_role():
    logger, handler = make_capture_handler()

    try:
        log_security_event(
            AUTHORIZATION_DENIED,
            username="operator",
            outcome="failure",
            reason="Administrator access required",
            role="operator",
        )
    finally:
        remove_capture_handler(logger, handler)

    record = handler.records[0]

    assert record.event == AUTHORIZATION_DENIED
    assert record.username == "operator"
    assert record.outcome == "failure"
    assert record.reason == (
        "Administrator access required"
    )
    assert record.role == "operator"


def test_security_event_does_not_accept_arbitrary_fields():
    logger, handler = make_capture_handler()

    try:
        log_security_event(
            LOGIN_SUCCESS,
            username="admin",
            outcome="success",
        )
    finally:
        remove_capture_handler(logger, handler)

    record = handler.records[0]

    assert not hasattr(
        record,
        "password",
    )

    assert not hasattr(
        record,
        "session_token",
    )

    assert not hasattr(
        record,
        "temporary_password",
    )

    assert not hasattr(
        record,
        "password_hash",
    )

    assert not hasattr(
        record,
        "secret",
    )


def test_security_event_does_not_log_sensitive_values():
    logger, handler = make_capture_handler()

    password = "CorrectPassword!"
    session_token = "super-secret-session-token"
    temporary_password = "Temporary-Password-123!"
    password_hash = "argon2-secret-hash"

    try:
        log_security_event(
            PASSWORD_CHANGED,
            username="admin",
            outcome="success",
        )

        log_security_event(
            PASSWORD_RESET,
            username="operator",
            outcome="success",
        )

        log_security_event(
            SESSION_REVOKED,
            username="admin",
            outcome="success",
        )
    finally:
        remove_capture_handler(logger, handler)

    rendered = "\n".join(
        record.getMessage()
        for record in handler.records
    )

    assert password not in rendered
    assert session_token not in rendered
    assert temporary_password not in rendered
    assert password_hash not in rendered


def test_security_event_names_are_stable():
    assert LOGIN_SUCCESS == "LOGIN_SUCCESS"
    assert LOGIN_FAILURE == "LOGIN_FAILURE"
    assert ACCOUNT_LOCKED == "ACCOUNT_LOCKED"
    assert LOGOUT == "LOGOUT"
    assert AUTHORIZATION_DENIED == "AUTHORIZATION_DENIED"
    assert SESSION_REVOKED == "SESSION_REVOKED"
    assert PASSWORD_CHANGED == "PASSWORD_CHANGED"
    assert PASSWORD_RESET == "PASSWORD_RESET"


def test_security_events_use_himp_security_logger():
    logger, handler = make_capture_handler()

    try:
        log_security_event(
            LOGOUT,
            username="admin",
            outcome="success",
        )
    finally:
        remove_capture_handler(logger, handler)

    assert handler.records[0].name == (
        "himp.security"
    )
