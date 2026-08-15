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


def test_authenticated_reports_page_exposes_operational_summary(
    monkeypatch,
):
    expected = {
        "generated": "2026-08-15T13:43:41Z",
        "dashboard": {
            "hosts": 43,
            "healthy": 3,
            "warnings": 0,
            "critical": 1,
            "unknown": 39,
            "average_score": 25.0,
        },
        "reports": {
            "current": 2,
            "history": 1,
            "health": 1,
            "discovery": 1,
            "json": 1,
        },
    }

    monkeypatch.setattr(
        server.himp.reports,
        "operational_summary",
        lambda: expected,
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/reports")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Reports" in response.text
    assert "Dashboard Report" in response.text
    assert "43" in response.text
    assert "25.0" in response.text


def test_reports_api_exposes_operational_summary(
    monkeypatch,
):
    expected = {
        "generated": "2026-08-15T13:43:41Z",
        "dashboard": {
            "hosts": 43,
            "healthy": 3,
            "warnings": 0,
            "critical": 1,
            "unknown": 39,
            "average_score": 25.0,
        },
        "reports": {
            "current": 2,
            "history": 1,
            "health": 1,
            "discovery": 1,
            "json": 1,
        },
    }

    monkeypatch.setattr(
        server.himp.reports,
        "operational_summary",
        lambda: expected,
    )

    server.app.dependency_overrides[
        server.require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/reports")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["operational_summary"] == expected
    assert "files" in response.json()
