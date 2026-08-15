from fastapi.testclient import TestClient

from himp.api import server
from himp.api.dependencies import require_session


def authenticated_session():
    return {
        "success": True,
        "username": "admin",
        "role": "admin",
    }


def test_application_health_api_returns_service_summary(
    monkeypatch,
):
    expected = {
        "status": "healthy",
        "components": {
            "database": {
                "status": "healthy",
                "message": "Database is available.",
            },
            "scheduler": {
                "status": "healthy",
                "message": "Scheduler is available.",
                "schedules": 2,
            },
            "automation": {
                "status": "healthy",
                "message": "Automation service is available.",
                "tasks": 5,
                "enabled": 4,
                "disabled": 1,
            },
            "configuration": {
                "status": "healthy",
                "message": "Required configuration paths exist.",
            },
            "storage": {
                "status": "healthy",
                "details": {
                    "data": True,
                    "reports": True,
                },
            },
        },
    }

    monkeypatch.setattr(
        server.himp.application_health,
        "summary",
        lambda: expected,
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/api/application-health"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == expected
