from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from himp.api import dependencies


class FakeSessionService:
    def __init__(self, result):
        self.result = result
        self.tokens = []

    def authenticate_session(self, token):
        self.tokens.append(token)
        return self.result


def make_request(token=None):
    headers = []

    if token is not None:
        headers.append(
            (
                b"cookie",
                f"himp_session={token}".encode(),
            )
        )

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "query_string": b"",
            "server": (
                "localhost",
                8000,
            ),
            "client": (
                "127.0.0.1",
                50000,
            ),
            "scheme": "http",
        }
    )


def test_require_session_returns_authenticated_session(
    monkeypatch,
):
    from himp.services.sessions import SessionResult

    now = datetime(
        2026,
        8,
        12,
        14,
        0,
    )

    result = SessionResult(
        success=True,
        username="admin",
        role="admin",
        created_at=now,
        expires_at=(
            now + timedelta(hours=8)
        ),
        last_seen_at=now,
    )

    service = FakeSessionService(result)

    monkeypatch.setattr(
        dependencies,
        "session_service",
        service,
    )

    request = make_request(
        "valid-session-token"
    )

    authenticated = dependencies.require_session(
        request
    )

    assert authenticated is result
    assert service.tokens == [
        "valid-session-token"
    ]


def test_require_session_rejects_missing_cookie(
    monkeypatch,
):
    from himp.services.sessions import SessionResult

    result = SessionResult(
        success=False,
        reason="Invalid session",
    )

    service = FakeSessionService(result)

    monkeypatch.setattr(
        dependencies,
        "session_service",
        service,
    )

    request = make_request()

    with pytest.raises(
        HTTPException
    ) as captured:
        dependencies.require_session(
            request
        )

    assert captured.value.status_code == 401
    assert captured.value.detail == (
        "Authentication required"
    )

    assert service.tokens == [None]


def test_require_session_rejects_invalid_cookie(
    monkeypatch,
):
    from himp.services.sessions import SessionResult

    result = SessionResult(
        success=False,
        reason="Invalid session",
    )

    service = FakeSessionService(result)

    monkeypatch.setattr(
        dependencies,
        "session_service",
        service,
    )

    request = make_request(
        "invalid-session-token"
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        dependencies.require_session(
            request
        )

    assert captured.value.status_code == 401
    assert captured.value.detail == (
        "Authentication required"
    )

    assert service.tokens == [
        "invalid-session-token"
    ]


def test_require_admin_allows_admin(
    monkeypatch,
):
    from himp.services.sessions import SessionResult

    result = SessionResult(
        success=True,
        username="admin",
        role="admin",
    )

    service = FakeSessionService(result)

    monkeypatch.setattr(
        dependencies,
        "session_service",
        service,
    )

    authenticated = dependencies.require_admin(
        make_request("admin-token")
    )

    assert authenticated is result


@pytest.mark.parametrize(
    "role",
    ["operator", "viewer"],
)
def test_require_admin_rejects_non_admin(
    monkeypatch,
    role,
):
    from himp.services.sessions import SessionResult

    result = SessionResult(
        success=True,
        username=role,
        role=role,
    )

    service = FakeSessionService(result)

    monkeypatch.setattr(
        dependencies,
        "session_service",
        service,
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        dependencies.require_admin(
            make_request(f"{role}-token")
        )

    assert captured.value.status_code == 403
    assert captured.value.detail == (
        "Administrator access required"
    )


def test_require_admin_logs_authorization_denied_for_non_admin(
    monkeypatch,
):
    import logging

    from himp.lib.security_events import (
        AUTHORIZATION_DENIED,
    )
    from himp.services.sessions import SessionResult

    session = SessionResult(
        success=True,
        username="operator",
        role="operator",
    )

    monkeypatch.setattr(
        dependencies,
        "require_session",
        lambda request: session,
    )

    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.security")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    request = make_request()

    try:
        with pytest.raises(HTTPException) as captured:
            dependencies.require_admin(request)
    finally:
        logger.removeHandler(handler)

    assert captured.value.status_code == 403
    assert captured.value.detail == (
        "Administrator access required"
    )

    assert len(records) == 1
    assert records[0].event == AUTHORIZATION_DENIED
    assert records[0].username == "operator"
    assert records[0].outcome == "failure"
    assert records[0].role == "operator"
    assert records[0].reason == (
        "Administrator access required"
    )


def test_require_admin_does_not_log_authorization_denial_for_admin(
    monkeypatch,
):
    import logging

    from himp.services.sessions import SessionResult

    session = SessionResult(
        success=True,
        username="admin",
        role="admin",
    )

    monkeypatch.setattr(
        dependencies,
        "require_session",
        lambda request: session,
    )

    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.security")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    request = make_request()

    try:
        result = dependencies.require_admin(request)
    finally:
        logger.removeHandler(handler)

    assert result is session
    assert records == []
