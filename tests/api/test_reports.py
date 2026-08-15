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
        "executions": {
            "total": 2,
            "successful": 1,
            "failed": 1,
            "recent": [
                {
                    "id": 3,
                    "task_id": "scheduled_updates",
                    "success": True,
                    "elapsed": 12.5,
                    "executed_at": "2026-08-15 14:00:00",
                },
                {
                    "id": 2,
                    "task_id": "generate_reports",
                    "success": False,
                    "elapsed": 4.25,
                    "executed_at": "2026-08-15 13:00:00",
                },
            ],
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
    assert "Execution History" in response.text
    assert "scheduled_updates" in response.text
    assert "generate_reports" in response.text
    assert "Successful" in response.text
    assert "Failed" in response.text


def test_authenticated_reports_page_exposes_pdf_download_link(
    monkeypatch,
):
    expected = {
        "generated": "2026-08-15T18:00:00Z",
        "dashboard": None,
        "reports": {},
        "executions": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "recent": [],
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
    assert 'href="/api/reports/pdf"' in response.text
    assert "Download PDF" in response.text
    assert "/api/reports/host/pve01/pdf" in response.text
    assert "/api/reports/host/pve01/txt" in response.text
    assert "/api/reports/host/pve01/csv" in response.text
    assert "PDF" in response.text
    assert "TXT" in response.text
    assert "CSV" in response.text


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
        "executions": {
            "total": 2,
            "successful": 1,
            "failed": 1,
            "recent": [
                {
                    "id": 3,
                    "task_id": "scheduled_updates",
                    "success": True,
                    "elapsed": 12.5,
                    "executed_at": "2026-08-15 14:00:00",
                },
                {
                    "id": 2,
                    "task_id": "generate_reports",
                    "success": False,
                    "elapsed": 4.25,
                    "executed_at": "2026-08-15 13:00:00",
                },
            ],
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
    assert response.json()["operational_summary"]["executions"] == {
        "total": 2,
        "successful": 1,
        "failed": 1,
        "recent": [
            {
                "id": 3,
                "task_id": "scheduled_updates",
                "success": True,
                "elapsed": 12.5,
                "executed_at": "2026-08-15 14:00:00",
            },
            {
                "id": 2,
                "task_id": "generate_reports",
                "success": False,
                "elapsed": 4.25,
                "executed_at": "2026-08-15 13:00:00",
            },
        ],
    }
    assert "files" in response.json()


def test_reports_pdf_api_returns_authenticated_pdf(
    monkeypatch,
):
    expected_summary = {
        "generated": "2026-08-15T18:00:00",
        "dashboard": None,
        "reports": {},
        "executions": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "recent": [],
        },
    }

    expected_pdf = b"%PDF-1.4\nHIMP TEST PDF"

    monkeypatch.setattr(
        server.himp.reports,
        "operational_summary",
        lambda: expected_summary,
    )

    class FakeReportPDFService:

        def generate(self, summary):
            assert summary == expected_summary
            return expected_pdf

    monkeypatch.setattr(
        "himp.services.report_pdf.ReportPDFService",
        FakeReportPDFService,
    )

    server.app.dependency_overrides[
        server.require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/api/reports/pdf"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.content == expected_pdf
    assert response.headers["content-type"] == (
        "application/pdf"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="himp-operational-report.pdf"'
    )


def test_reports_pdf_api_requires_session():
    with TestClient(server.app) as client:
        response = client.get(
            "/api/reports/pdf"
        )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication required"
    )


def test_host_report_pdf_api_returns_authenticated_pdf(
    monkeypatch,
):
    expected_pdf = b"%PDF-1.4\nHOST TEST PDF"

    class FakeHostReportExportService:

        def pdf(self, hostname):
            assert hostname == "pve01"
            return expected_pdf

    monkeypatch.setattr(
        "himp.services.host_report_export.HostReportExportService",
        FakeHostReportExportService,
    )

    server.app.dependency_overrides[
        server.require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/api/reports/host/pve01/pdf"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.content == expected_pdf
    assert response.headers["content-type"] == (
        "application/pdf"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="pve01-report.pdf"'
    )


def test_host_report_txt_api_returns_authenticated_text(
    monkeypatch,
):
    expected_text = "Host: pve01\nStatus: healthy\n"

    class FakeHostReportExportService:

        def txt(self, hostname):
            assert hostname == "pve01"
            return expected_text

    monkeypatch.setattr(
        "himp.services.host_report_export.HostReportExportService",
        FakeHostReportExportService,
    )

    server.app.dependency_overrides[
        server.require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/api/reports/host/pve01/txt"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == expected_text
    assert response.headers["content-type"] == (
        "text/plain; charset=utf-8"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="pve01-report.txt"'
    )


def test_host_report_csv_api_returns_authenticated_csv(
    monkeypatch,
):
    expected_csv = "hostname,status\npve01,healthy\n"

    class FakeHostReportExportService:

        def csv(self, hostname):
            assert hostname == "pve01"
            return expected_csv

    monkeypatch.setattr(
        "himp.services.host_report_export.HostReportExportService",
        FakeHostReportExportService,
    )

    server.app.dependency_overrides[
        server.require_session
    ] = authenticated_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/api/reports/host/pve01/csv"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == expected_csv
    assert response.headers["content-type"] == (
        "text/csv; charset=utf-8"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="pve01-report.csv"'
    )


def test_host_report_exports_require_session():
    with TestClient(server.app) as client:
        pdf = client.get(
            "/api/reports/host/pve01/pdf"
        )
        txt = client.get(
            "/api/reports/host/pve01/txt"
        )
        csv = client.get(
            "/api/reports/host/pve01/csv"
        )

    assert pdf.status_code == 401
    assert txt.status_code == 401
    assert csv.status_code == 401
