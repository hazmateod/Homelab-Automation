from datetime import datetime

from fastapi.testclient import TestClient

from himp.api import server
from himp.api.dependencies import require_admin, require_session
from himp.services.sessions import SessionResult


def authenticated_session(
    username="viewer",
    role="viewer",
):
    now = datetime(
        2026,
        8,
        12,
        14,
        0,
    )

    return SessionResult(
        success=True,
        username=username,
        role=role,
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )


def test_anonymous_api_health_is_rejected():
    with TestClient(server.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required"
    }


def test_anonymous_system_status_is_rejected():
    with TestClient(server.app) as client:
        response = client.get("/system/status")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required"
    }


def test_anonymous_system_restart_is_rejected():
    with TestClient(server.app) as client:
        response = client.post("/system/restart")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required"
    }


def test_anonymous_direct_api_route_is_rejected():
    with TestClient(server.app) as client:
        response = client.get("/api")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required"
    }


def test_viewer_cannot_restart_himp():
    server.app.dependency_overrides[
        require_session
    ] = lambda: authenticated_session()

    server.app.dependency_overrides[
        require_admin
    ] = lambda: (_ for _ in ()).throw(
        __import__("fastapi").HTTPException(
            status_code=403,
            detail="Administrator access required",
        )
    )

    try:
        with TestClient(server.app) as client:
            response = client.post(
                "/system/restart"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Administrator access required"
    }


def test_admin_can_reach_restart_endpoint_without_executing_restart(
    monkeypatch,
):
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append(
            {
                "args": args,
                "kwargs": kwargs,
            }
        )

    monkeypatch.setattr(
        server.subprocess,
        "Popen",
        fake_popen,
    )

    server.app.dependency_overrides[
        require_admin
    ] = lambda: authenticated_session(
        username="admin",
        role="admin",
    )

    try:
        with TestClient(server.app) as client:
            response = client.post(
                "/system/restart"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "restart_requested"
    }

    assert len(calls) == 1
    assert calls[0]["args"][0] == [
        "bash",
        "-c",
        "sleep 1 && systemctl restart himp",
    ]
    assert calls[0]["kwargs"]["start_new_session"] is True


def test_health_execution_requires_admin_and_uses_server_selected_group(monkeypatch):
    from himp.api import dependencies, health

    calls = []
    monkeypatch.setattr(health.service, "plugin", lambda name: calls.append(name) or {"plugin": name})
    path = "/api/health/technitium"
    with TestClient(server.app) as client:
        assert client.get(path).status_code == 401

        for role, status in (("viewer", 403), ("admin", 200)):
            monkeypatch.setattr(
                dependencies.session_service, "authenticate_session",
                lambda token: authenticated_session(role=role),
            )
            response = client.get(path, params={"inventory_group": "other", "hosts": "outside"})
            assert response.status_code == status

    assert calls == ["technitium"]


def test_workflow_execution_requires_administrator_session(monkeypatch):
    from himp.api import dependencies, workflows

    calls = []
    monkeypatch.setattr(
        workflows.workflow_execution_service, "execute",
        lambda workflow_id, **kwargs: calls.append((workflow_id, kwargs)) or {"success": True},
    )
    with TestClient(server.app) as client:
        path = "/api/workflows/17/execute"
        assert client.post(path).status_code == 401
        for role, status in (("viewer", 403), ("operator", 403), ("admin", 200)):
            monkeypatch.setattr(
                dependencies.session_service, "authenticate_session",
                lambda token: authenticated_session(role=role),
            )
            assert client.post(path, json={"confirmed": True}).status_code == status
    assert calls == [(17, {"limit": None, "confirmed": True})]
