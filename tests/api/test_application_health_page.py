from datetime import datetime

from fastapi.testclient import TestClient

from himp.api import server
from himp.api.dependencies import require_page_session
from himp.services.sessions import SessionResult


def authenticated_session():
    now = datetime(
        2026,
        8,
        15,
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


def test_authenticated_application_health_page_exposes_summary(
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
        require_page_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/application-health"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Application Health" in response.text
    assert "Database" in response.text
    assert "Scheduler" in response.text
    assert "Automation" in response.text
    assert "Configuration" in response.text
    assert "Storage" in response.text
    assert "healthy" in response.text.lower()
