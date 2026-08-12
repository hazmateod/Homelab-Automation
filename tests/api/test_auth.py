from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from himp.api import auth


class FakeAuthenticationService:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def authenticate(
        self,
        username,
        password,
    ):
        self.calls.append(
            (username, password)
        )
        return self.result


class FakeSessionService:
    SESSION_LIFETIME = timedelta(hours=8)

    def __init__(
        self,
        create_result=None,
        authenticate_result=None,
    ):
        self.create_result = create_result
        self.authenticate_result = authenticate_result
        self.created = []
        self.authenticated = []
        self.revoked = []

    def create_session(self, username):
        self.created.append(username)
        return self.create_result

    def authenticate_session(self, token):
        self.authenticated.append(token)
        return self.authenticate_result

    def revoke_session(self, token):
        self.revoked.append(token)
        return True


def make_request(
    cookies=None,
):
    headers = []

    if cookies:
        cookie_header = "; ".join(
            f"{key}={value}"
            for key, value in cookies.items()
        )
        headers.append(
            (
                b"cookie",
                cookie_header.encode(),
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


def test_login_creates_session_and_sets_cookie(
    monkeypatch,
):
    from himp.services.authentication import (
        AuthenticationResult,
    )
    from himp.services.sessions import (
        SessionResult,
    )

    authentication = FakeAuthenticationService(
        AuthenticationResult(
            success=True,
            username="admin",
            role="admin",
            display_name="Administrator",
            password_change_required=False,
        )
    )

    created = datetime(
        2026,
        8,
        12,
        14,
        0,
    )

    session = FakeSessionService(
        create_result=SessionResult(
            success=True,
            token="test-session-token",
            username="admin",
            created_at=created,
            expires_at=(
                created + timedelta(hours=8)
            ),
            last_seen_at=created,
        )
    )

    monkeypatch.setattr(
        auth,
        "authentication_service",
        authentication,
    )

    monkeypatch.setattr(
        auth,
        "session_service",
        session,
    )

    response = Response()

    result = await_login(
        auth.login(
            auth.LoginRequest(
                username="admin",
                password="CorrectPassword!",
            ),
            response,
        )
    )

    assert result == {
        "username": "admin",
        "role": "admin",
        "display_name": "Administrator",
        "password_change_required": False,
        "expires_at": (
            "2026-08-12T22:00:00"
        ),
    }

    assert authentication.calls == [
        (
            "admin",
            "CorrectPassword!",
        )
    ]

    assert session.created == ["admin"]

    set_cookie = response.headers["set-cookie"]

    assert "himp_session=test-session-token" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_login_rejects_invalid_credentials(
    monkeypatch,
):
    from himp.services.authentication import (
        AuthenticationResult,
    )

    authentication = FakeAuthenticationService(
        AuthenticationResult(
            success=False,
            reason="Invalid credentials",
        )
    )

    session = FakeSessionService()

    monkeypatch.setattr(
        auth,
        "authentication_service",
        authentication,
    )

    monkeypatch.setattr(
        auth,
        "session_service",
        session,
    )

    response = Response()

    with pytest.raises(
        HTTPException
    ) as captured:
        await_login(
            auth.login(
                auth.LoginRequest(
                    username="admin",
                    password="wrong",
                ),
                response,
            )
        )

    assert captured.value.status_code == 401
    assert captured.value.detail == (
        "Invalid credentials"
    )

    assert session.created == []


def test_login_rejects_locked_account(
    monkeypatch,
):
    from himp.services.authentication import (
        AuthenticationResult,
    )

    authentication = FakeAuthenticationService(
        AuthenticationResult(
            success=False,
            reason="Account locked",
        )
    )

    monkeypatch.setattr(
        auth,
        "authentication_service",
        authentication,
    )

    response = Response()

    with pytest.raises(
        HTTPException
    ) as captured:
        await_login(
            auth.login(
                auth.LoginRequest(
                    username="admin",
                    password="wrong",
                ),
                response,
            )
        )

    assert captured.value.status_code == 403
    assert captured.value.detail == (
        "Account locked"
    )


def test_current_user_requires_session(
    monkeypatch,
):
    from himp.services.sessions import (
        SessionResult,
    )

    session = FakeSessionService(
        authenticate_result=SessionResult(
            success=False,
            reason="Invalid session",
        )
    )

    monkeypatch.setattr(
        auth,
        "session_service",
        session,
    )

    request = make_request()

    with pytest.raises(
        HTTPException
    ) as captured:
        await_current_user(
            auth.current_user(request)
        )

    assert captured.value.status_code == 401
    assert captured.value.detail == (
        "Authentication required"
    )

    assert session.authenticated == [None]


def test_current_user_returns_session(
    monkeypatch,
):
    from himp.services.sessions import (
        SessionResult,
    )

    created = datetime(
        2026,
        8,
        12,
        14,
        0,
    )

    session = FakeSessionService(
        authenticate_result=SessionResult(
            success=True,
            username="admin",
            created_at=created,
            expires_at=(
                created + timedelta(hours=8)
            ),
            last_seen_at=(
                created + timedelta(minutes=5)
            ),
        )
    )

    monkeypatch.setattr(
        auth,
        "session_service",
        session,
    )

    request = make_request(
        {
            "himp_session": "test-token"
        }
    )

    result = await_current_user(
        auth.current_user(request)
    )

    assert result == {
        "username": "admin",
        "created_at": (
            "2026-08-12T14:00:00"
        ),
        "expires_at": (
            "2026-08-12T22:00:00"
        ),
        "last_seen_at": (
            "2026-08-12T14:05:00"
        ),
    }

    assert session.authenticated == [
        "test-token"
    ]


def test_logout_revokes_session_and_deletes_cookie(
    monkeypatch,
):
    session = FakeSessionService()

    monkeypatch.setattr(
        auth,
        "session_service",
        session,
    )

    request = make_request(
        {
            "himp_session": "test-token"
        }
    )

    response = Response()

    result = await_logout(
        auth.logout(
            request,
            response,
        )
    )

    assert result == {
        "success": True,
        "message": (
            "Logged out successfully."
        ),
    }

    assert session.revoked == [
        "test-token"
    ]

    assert "himp_session=" in (
        response.headers["set-cookie"]
    )


def test_logout_without_session_still_succeeds(
    monkeypatch,
):
    session = FakeSessionService()

    monkeypatch.setattr(
        auth,
        "session_service",
        session,
    )

    request = make_request()
    response = Response()

    result = await_logout(
        auth.logout(
            request,
            response,
        )
    )

    assert result["success"] is True
    assert session.revoked == []


def await_login(coroutine):
    import asyncio

    return asyncio.run(coroutine)


def await_current_user(coroutine):
    import asyncio

    return asyncio.run(coroutine)


def await_logout(coroutine):
    import asyncio

    return asyncio.run(coroutine)
