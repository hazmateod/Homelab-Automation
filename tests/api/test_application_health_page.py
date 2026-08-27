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


def empty_operational_summary():
    return {
        "status": "PASS",
        "health": {},
        "workflows": {},
        "automations": {},
        "remediation": {},
        "attention": [],
    }


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
        "release": {
            "available": False,
            "revision": None,
        },
        "scheduler_operations": {
            "available": True,
            "total": 0,
            "enabled": 0,
            "disabled": 0,
            "failed": 0,
            "schedules": [],
        },
        "maintenance": {
            "available": True,
            "active_count": 0,
            "upcoming_count": 0,
            "active": [],
            "upcoming": [],
        },
        "infrastructure": {
            "available": True,
            "total": 0,
            "passed": 0,
            "warnings": 0,
            "failed": 0,
            "unknown": 0,
            "score": 0,
        },
    }

    monkeypatch.setattr(
        server.himp.application_health,
        "summary",
        lambda: expected,
    )

    monkeypatch.setattr(
        server.himp.dashboard,
        "operational_summary",
        empty_operational_summary,
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
    assert "Application Operations" in response.text
    assert "Database" in response.text
    assert "Scheduler" in response.text
    assert "Automation" in response.text
    assert "Configuration" in response.text
    assert "Storage" in response.text
    assert "healthy" in response.text.lower()


def test_application_health_page_exposes_operations_overview(
    monkeypatch,
):
    expected = {
        "status": "healthy",
        "components": {
            "database": {
                "status": "healthy",
                "message": "Database is available.",
            },
        },
        "release": {
            "available": True,
            "revision": "abc123",
        },
        "scheduler_operations": {
            "available": True,
            "total": 2,
            "enabled": 1,
            "disabled": 1,
            "failed": 1,
            "schedules": [
                {
                    "task_id": "health_check",
                    "name": "Health Check",
                    "enabled": True,
                    "frequency": "hourly",
                    "next_run": "2026-08-28T01:00:00",
                    "last_execution_success": True,
                    "last_execution_at": "2026-08-28T00:00:00",
                    "last_execution_elapsed": 1.25,
                    "last_execution_error": None,
                },
            ],
        },
        "maintenance": {
            "available": True,
            "active_count": 1,
            "upcoming_count": 1,
            "active": [
                {
                    "name": "Active Maintenance",
                    "starts_at": "2026-08-27T22:00:00",
                    "ends_at": "2026-08-28T00:30:00",
                    "task_id": None,
                },
            ],
            "upcoming": [
                {
                    "name": "Upcoming Maintenance",
                    "starts_at": "2026-08-29T01:00:00",
                    "ends_at": "2026-08-29T02:00:00",
                    "task_id": "scheduled_updates",
                },
            ],
        },
        "infrastructure": {
            "available": True,
            "total": 45,
            "passed": 42,
            "warnings": 1,
            "failed": 1,
            "unknown": 1,
            "score": 94,
        },
    }

    monkeypatch.setattr(
        server.himp.application_health,
        "summary",
        lambda: expected,
    )

    monkeypatch.setattr(
        server.himp.dashboard,
        "operational_summary",
        empty_operational_summary,
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
    assert "Application Operations" in response.text
    assert "abc123" in response.text
    assert "Scheduler Operations" in response.text
    assert "Health Check" in response.text
    assert "Active Maintenance" in response.text
    assert "Upcoming Maintenance" in response.text
    assert "Infrastructure Health" in response.text
    assert "94%" in response.text
    assert "Manage Automation" in response.text


def test_sidebar_exposes_application_operations_navigation():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]

    source = (
        root
        / "templates"
        / "layout"
        / "sidebar.html"
    ).read_text(encoding="utf-8")

    assert 'href="/application-health"' in source
    assert "Operations" in source


def test_application_health_page_exposes_operational_attention(
    monkeypatch,
):
    application_summary = {
        "status": "healthy",
        "components": {},
        "release": {
            "available": False,
            "revision": None,
        },
        "scheduler_operations": {
            "available": True,
            "total": 0,
            "enabled": 0,
            "disabled": 0,
            "failed": 0,
            "schedules": [],
        },
        "maintenance": {
            "available": True,
            "active_count": 0,
            "upcoming_count": 0,
            "active": [],
            "upcoming": [],
        },
        "infrastructure": {
            "available": True,
            "total": 0,
            "passed": 0,
            "warnings": 0,
            "failed": 0,
            "unknown": 0,
            "score": 0,
        },
    }

    operational_summary = {
        "status": "FAIL",
        "health": {},
        "workflows": {},
        "automations": {},
        "remediation": {},
        "attention": [
            {
                "severity": "FAIL",
                "category": "Host Connectivity",
                "message": (
                    "1 host(s) failed connectivity checks."
                ),
                "href": "/health",
            },
            {
                "severity": "WARNING",
                "category": "Remediation",
                "message": (
                    "2 remediation recommendation(s) "
                    "await confirmation."
                ),
                "href": "/remediation",
            },
        ],
    }

    monkeypatch.setattr(
        server.himp.application_health,
        "summary",
        lambda: application_summary,
    )

    monkeypatch.setattr(
        server.himp.dashboard,
        "operational_summary",
        lambda: operational_summary,
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
    assert "Operational Attention" in response.text
    assert "Host Connectivity" in response.text
    assert "1 host(s) failed connectivity checks." in response.text
    assert 'href="/health"' in response.text
    assert "Remediation" in response.text
    assert "await confirmation" in response.text
    assert 'href="/remediation"' in response.text
    assert "FAIL" in response.text
    assert "WARNING" in response.text


def test_application_health_page_exposes_attention_pass_state(
    monkeypatch,
):
    application_summary = {
        "status": "healthy",
        "components": {},
        "release": {
            "available": False,
            "revision": None,
        },
        "scheduler_operations": {
            "available": True,
            "total": 0,
            "enabled": 0,
            "disabled": 0,
            "failed": 0,
            "schedules": [],
        },
        "maintenance": {
            "available": True,
            "active_count": 0,
            "upcoming_count": 0,
            "active": [],
            "upcoming": [],
        },
        "infrastructure": {
            "available": True,
            "total": 0,
            "passed": 0,
            "warnings": 0,
            "failed": 0,
            "unknown": 0,
            "score": 0,
        },
    }

    operational_summary = {
        "status": "PASS",
        "health": {},
        "workflows": {},
        "automations": {},
        "remediation": {},
        "attention": [],
    }

    monkeypatch.setattr(
        server.himp.application_health,
        "summary",
        lambda: application_summary,
    )

    monkeypatch.setattr(
        server.himp.dashboard,
        "operational_summary",
        lambda: operational_summary,
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
    assert "Operational Attention" in response.text
    assert (
        "No current operational conditions require attention."
        in response.text
    )
    assert "PASS" in response.text
