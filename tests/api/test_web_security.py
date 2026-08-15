from datetime import datetime

from fastapi.testclient import TestClient

from himp.api import server
from himp.api.dependencies import require_page_session
from himp.services.sessions import SessionResult


def authenticated_session():
    now = datetime(
        2026,
        8,
        12,
        14,
        0,
    )

    return SessionResult(
        success=True,
        username="admin",
        role="admin",
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )


def test_login_page_is_public():
    with TestClient(server.app) as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert "HIMP Login" in response.text


def test_anonymous_home_redirects_to_login():
    with TestClient(server.app) as client:
        response = client.get(
            "/",
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_anonymous_inventory_redirects_to_login():
    with TestClient(server.app) as client:
        response = client.get(
            "/inventory",
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_authenticated_home_is_allowed():
    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "dashboard" in response.text.lower()


def test_authenticated_inventory_is_allowed():
    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/inventory")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "inventory" in response.text.lower()


def test_static_assets_remain_public():
    with TestClient(server.app) as client:
        response = client.get(
            "/static/js/dashboard.js"
        )

    assert response.status_code == 200


def test_login_cookie_is_not_secure_over_http(
    monkeypatch,
):
    from himp.api import auth
    from himp.services.authentication import AuthenticationResult
    from himp.services.sessions import SessionResult

    now = datetime(
        2026,
        8,
        12,
        14,
        0,
    )

    monkeypatch.setattr(
        auth,
        "authentication_service",
        type(
            "FakeAuthentication",
            (),
            {
                "authenticate": lambda self, username, password:
                    AuthenticationResult(
                        success=True,
                        username=username,
                        role="admin",
                        display_name="Administrator",
                        password_change_required=False,
                    )
            },
        )(),
    )

    monkeypatch.setattr(
        auth,
        "session_service",
        type(
            "FakeSession",
            (),
            {
                "create_session": lambda self, username:
                    SessionResult(
                        success=True,
                        token="test-token",
                        username=username,
                        role="admin",
                        created_at=now,
                        expires_at=now,
                        last_seen_at=now,
                    )
            },
        )(),
    )

    with TestClient(server.app, base_url="http://testserver") as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "CorrectPassword!",
            },
        )

    cookie = response.headers["set-cookie"]

    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie


def test_login_cookie_is_secure_over_https(
    monkeypatch,
):
    from himp.api import auth
    from himp.services.authentication import AuthenticationResult
    from himp.services.sessions import SessionResult

    now = datetime(
        2026,
        8,
        12,
        14,
        0,
    )

    monkeypatch.setattr(
        auth,
        "authentication_service",
        type(
            "FakeAuthentication",
            (),
            {
                "authenticate": lambda self, username, password:
                    AuthenticationResult(
                        success=True,
                        username=username,
                        role="admin",
                        display_name="Administrator",
                        password_change_required=False,
                    )
            },
        )(),
    )

    monkeypatch.setattr(
        auth,
        "session_service",
        type(
            "FakeSession",
            (),
            {
                "create_session": lambda self, username:
                    SessionResult(
                        success=True,
                        token="test-token",
                        username=username,
                        role="admin",
                        created_at=now,
                        expires_at=now,
                        last_seen_at=now,
                    )
            },
        )(),
    )

    with TestClient(server.app, base_url="https://testserver") as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "CorrectPassword!",
            },
        )

    cookie = response.headers["set-cookie"]

    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie


def test_anonymous_remediation_redirects_to_login():
    with TestClient(server.app) as client:
        response = client.get(
            "/remediation",
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_authenticated_remediation_is_allowed(
    monkeypatch,
):
    monkeypatch.setattr(
        server.remediation_audit_repository,
        "history",
        lambda limit=50: [],
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/remediation")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Remediation" in response.text
    assert 'href="/remediation"' in response.text
    assert "No remediation audit records are available." in response.text
