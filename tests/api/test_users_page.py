from datetime import datetime

from fastapi import HTTPException
from fastapi.testclient import TestClient

from himp.api import server
from himp.api.dependencies import (
    require_page_admin,
    require_page_session,
    require_page_session,
)
from himp.services.sessions import SessionResult


def authenticated_admin():
    now = datetime(
        2026,
        8,
        15,
        17,
        30,
    )

    return SessionResult(
        success=True,
        username="admin",
        role="admin",
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )


def authenticated_operator():
    now = datetime(
        2026,
        8,
        15,
        17,
        30,
    )

    return SessionResult(
        success=True,
        username="operator1",
        role="operator",
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )


def test_anonymous_users_page_redirects_to_login():
    with TestClient(server.app) as client:
        response = client.get(
            "/users",
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_non_admin_users_page_is_forbidden():
    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_operator

    try:
        with TestClient(server.app) as client:
            response = client.get("/users")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Administrator access required"
    }


def test_admin_users_page_is_allowed(monkeypatch):
    expected_users = [
        {
            "username": "admin",
            "role": "admin",
            "active": True,
            "display_name": "Administrator",
        },
        {
            "username": "operator1",
            "role": "operator",
            "active": True,
            "display_name": "Operator One",
        },
    ]

    class FakeUserManagement:
        def list_users(self):
            return expected_users

    from himp.api import users

    monkeypatch.setattr(
        users,
        "user_management",
        FakeUserManagement(),
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_admin

    try:
        with TestClient(server.app) as client:
            response = client.get("/users")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "User Management" in response.text
    assert "Administrator" in response.text
    assert "Operator One" in response.text
    assert "admin" in response.text
    assert "operator1" in response.text
