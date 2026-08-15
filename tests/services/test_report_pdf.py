from io import BytesIO

from pypdf import PdfReader

from himp.services.report_pdf import ReportPDFService


def make_summary():
    return {
        "generated": "2026-08-15T18:00:00",
        "dashboard": {
            "hosts": 10,
            "healthy": 7,
            "warnings": 2,
            "critical": 1,
            "unknown": 0,
            "average_score": 87.5,
        },
        "reports": {
            "current": 10,
            "history": 25,
            "health": 10,
            "discovery": 5,
            "json": 15,
        },
        "executions": {
            "total": 3,
            "successful": 2,
            "failed": 1,
            "recent": [
                {
                    "id": 101,
                    "task_id": "health_check",
                    "success": True,
                    "elapsed": 12.5,
                    "executed_at": "2026-08-15T17:00:00",
                },
                {
                    "id": 100,
                    "task_id": "maintenance",
                    "success": False,
                    "elapsed": 8.25,
                    "executed_at": "2026-08-15T16:00:00",
                },
            ],
        },
    }


def extract_text(pdf):
    reader = PdfReader(BytesIO(pdf))

    return "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )


def test_generate_returns_pdf_bytes():
    service = ReportPDFService()

    pdf = service.generate(
        make_summary()
    )

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_generate_includes_expected_report_content():
    service = ReportPDFService()

    pdf = service.generate(
        make_summary()
    )

    text = extract_text(pdf)

    assert "HIMP Operational Report" in text
    assert "Dashboard Summary" in text
    assert "Report Inventory" in text
    assert "Execution Summary" in text
    assert "Recent Execution History" in text


def test_generate_handles_missing_dashboard_and_empty_history():
    service = ReportPDFService()

    summary = {
        "generated": None,
        "dashboard": None,
        "reports": {},
        "executions": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "recent": [],
        },
    }

    pdf = service.generate(summary)

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")

    text = extract_text(pdf)

    assert (
        "No dashboard report is currently available."
        in text
    )
    assert (
        "No automation execution history is currently available."
        in text
    )
