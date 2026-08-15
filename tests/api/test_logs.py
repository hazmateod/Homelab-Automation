from fastapi.testclient import TestClient

from himp.api import server
from himp.api.dependencies import require_page_session, require_session


def authenticated_session():
    return {"username": "test-admin"}


def test_logs_api_requires_session():
    with TestClient(server.app) as client:
        response = client.get("/api/logs")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication required"
    )


def test_logs_api_returns_normalized_records(monkeypatch):
    expected = [
        {
            "id": "automation:1",
            "timestamp": "2026-08-15 14:00:00",
            "source": "automation",
            "event": "automation_execution",
            "status": "success",
            "message": "Automation execution: scheduled_updates",
            "details": {
                "task_id": "scheduled_updates",
            },
        }
    ]

    monkeypatch.setattr(
        server.log_service,
        "history",
        lambda limit: expected,
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/logs?limit=25")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "logs": expected,
        "limit": 25,
    }


def test_logs_api_clamps_limit(monkeypatch):
    captured = {}

    def fake_history(limit):
        captured["limit"] = limit
        return []

    monkeypatch.setattr(
        server.log_service,
        "history",
        fake_history,
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/logs?limit=9999")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["limit"] == 500
    assert response.json()["limit"] == 500


def test_authenticated_history_page_uses_log_service(monkeypatch):
    expected = [
        {
            "id": "automation:1",
            "timestamp": "2026-08-15 14:00:00",
            "source": "automation",
            "event": "automation_execution",
            "status": "success",
            "message": "Automation execution: scheduled_updates",
            "details": {
                "task_id": "scheduled_updates",
            },
        }
    ]

    monkeypatch.setattr(
        server.log_service,
        "history",
        lambda limit: expected,
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/history")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Operational Logs" in response.text
    assert "automation_execution" in response.text
    assert "scheduled_updates" in response.text
    assert "View Details" in response.text


def test_history_page_requires_session():
    with TestClient(server.app) as client:
        response = client.get(
            "/history",
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_logs_json_export_requires_session():
    with TestClient(server.app) as client:
        response = client.get("/api/logs/export/json")

    assert response.status_code == 401


def test_logs_json_export_returns_json(monkeypatch):
    expected = [
        {
            "id": "automation:1",
            "timestamp": "2026-08-15 14:00:00",
            "source": "automation",
            "event": "automation_execution",
            "status": "success",
            "message": "Automation execution: scheduled_updates",
            "details": {"task_id": "scheduled_updates"},
        }
    ]

    monkeypatch.setattr(
        server.log_service,
        "history",
        lambda limit: expected,
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/logs/export/json")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/json"
    )
    assert "attachment" in response.headers["content-disposition"]
    assert "himp-operational-logs.json" in (
        response.headers["content-disposition"]
    )
    assert response.json() == expected


def test_logs_txt_export_returns_text(monkeypatch):
    expected = [
        {
            "id": "automation:1",
            "timestamp": "2026-08-15 14:00:00",
            "source": "automation",
            "event": "automation_execution",
            "status": "success",
            "message": "Automation execution: scheduled_updates",
            "details": {"task_id": "scheduled_updates"},
        }
    ]

    monkeypatch.setattr(
        server.log_service,
        "history",
        lambda limit: expected,
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/logs/export/txt")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/plain"
    )
    assert "himp-operational-logs.txt" in (
        response.headers["content-disposition"]
    )
    assert "Automation execution: scheduled_updates" in (
        response.text
    )


def test_logs_csv_export_returns_csv(monkeypatch):
    expected = [
        {
            "id": "automation:1",
            "timestamp": "2026-08-15 14:00:00",
            "source": "automation",
            "event": "automation_execution",
            "status": "success",
            "message": "Automation execution: scheduled_updates",
            "details": {"task_id": "scheduled_updates"},
        }
    ]

    monkeypatch.setattr(
        server.log_service,
        "history",
        lambda limit: expected,
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/logs/export/csv")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/csv"
    )
    assert "himp-operational-logs.csv" in (
        response.headers["content-disposition"]
    )
    assert "automation:1" in response.text
    assert "scheduled_updates" in response.text


def test_logs_csv_export_truncates_oversized_details(monkeypatch):
    oversized_details = {
        "host_health_check": "X" * 40000,
    }

    expected = [
        {
            "id": "automation:oversized",
            "timestamp": "2026-08-15 14:00:00",
            "source": "automation",
            "event": "automation_execution",
            "status": "success",
            "message": "Automation execution: host_health_check",
            "details": oversized_details,
        }
    ]

    monkeypatch.setattr(
        server.log_service,
        "history",
        lambda limit: expected,
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/logs/export/csv")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/csv"
    )

    import csv
    import io

    rows = list(csv.reader(io.StringIO(response.text)))

    assert len(rows) == 2

    header = rows[0]
    data = rows[1]

    details_index = header.index("details")
    details = data[details_index]

    assert len(details) <= 32767
    assert details.endswith("[truncated]")
    assert "host_health_check" in details
