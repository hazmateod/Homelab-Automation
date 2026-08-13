"""
Tests for the HIMP API error boundary.
"""

from fastapi import APIRouter

from himp.api import server


def test_unexpected_exception_returns_safe_500_response():
    router = APIRouter()

    @router.get("/__test/unexpected-error")
    def unexpected_error():
        raise RuntimeError(
            "SECRET_INTERNAL_FAILURE /opt/private/database.db"
        )

    server.app.include_router(router)

    from fastapi.testclient import TestClient

    with TestClient(server.app, raise_server_exceptions=False) as client:
        response = client.get(
            "/__test/unexpected-error"
        )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error"
    }

    body = response.text

    assert "SECRET_INTERNAL_FAILURE" not in body
    assert "/opt/private/database.db" not in body
    assert "Traceback" not in body


def test_http_exception_behavior_remains_unchanged():
    from fastapi import HTTPException

    router = APIRouter()

    @router.get("/__test/http-error")
    def http_error():
        raise HTTPException(
            status_code=404,
            detail="Resource not found",
        )

    server.app.include_router(router)

    from fastapi.testclient import TestClient

    with TestClient(server.app) as client:
        response = client.get(
            "/__test/http-error"
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Resource not found"
    }


def test_automation_endpoint_hides_unexpected_exception():
    from himp.api.dependencies import require_session

    class FakeAutomation:
        def run(self, task_id, confirmed=False):
            raise RuntimeError(
                "SECRET_AUTOMATION_FAILURE /opt/private/automation.db"
            )

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    from himp.api import automation

    original_himp = automation.himp

    server.app.dependency_overrides[
        require_session
    ] = lambda: {
        "username": "admin",
        "role": "admin",
    }

    automation.himp = FakeHIMP()

    try:
        from fastapi.testclient import TestClient

        with TestClient(
            server.app,
            raise_server_exceptions=False,
        ) as client:
            response = client.post(
                "/api/automation/health_check/run",
                json={"confirmed": True},
            )
    finally:
        automation.himp = original_himp
        server.app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error"
    }

    body = response.text

    assert "SECRET_AUTOMATION_FAILURE" not in body
    assert "/opt/private/automation.db" not in body
    assert "Traceback" not in body
