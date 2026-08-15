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


def test_authenticated_remediation_renders_audit_record(
    monkeypatch,
):
    monkeypatch.setattr(
        server.remediation_audit_repository,
        "history",
        lambda limit=50, source_type=None, source_id=None, decision=None: [
            {
                "id": 42,
                "source_type": "host",
                "source_id": "pve02",
                "task_id": "scheduled_updates",
                "decision": "ALLOW",
                "reason": "Package drift detected",
                "evidence": {},
                "risk_level": "LOW",
                "confirmation_required": False,
                "confirmed": False,
                "execution_id": 123,
                "execution_success": True,
                "created_at": "2026-08-15 08:00:00",
            }
        ],
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
    assert "pve02" in response.text
    assert "scheduled_updates" in response.text
    assert "ALLOW" in response.text
    assert "LOW" in response.text
    assert "SUCCESS" in response.text
    assert "ID 123" in response.text
    assert "No remediation audit records are available." not in response.text
    assert "Package drift detected" in response.text


def test_authenticated_remediation_passes_audit_filters(
    monkeypatch,
):
    captured = {}

    def fake_history(
        limit=50,
        source_type=None,
        source_id=None,
        decision=None,
    ):
        captured["limit"] = limit
        captured["source_type"] = source_type
        captured["source_id"] = source_id
        captured["decision"] = decision
        return []

    monkeypatch.setattr(
        server.remediation_audit_repository,
        "history",
        fake_history,
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/remediation",
                params={
                    "source_type": "host",
                    "source_id": "pve02",
                    "decision": "ALLOW",
                },
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "limit": 50,
        "source_type": "host",
        "source_id": "pve02",
        "decision": "ALLOW",
    }


def test_authenticated_remediation_is_allowed(
    monkeypatch,
):
    monkeypatch.setattr(
        server.remediation_audit_repository,
        "history",
        lambda limit=50, source_type=None, source_id=None, decision=None: [],
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
    assert 'name="source_type"' in response.text
    assert 'name="source_id"' in response.text
    assert 'name="decision"' in response.text
    assert 'action="/remediation"' in response.text
    assert "All Decisions" in response.text
    assert "No remediation audit records are available." in response.text
