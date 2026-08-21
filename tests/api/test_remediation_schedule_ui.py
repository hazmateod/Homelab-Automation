from pathlib import Path


def test_remediation_template_contains_schedule_controls():
    content = Path(
        "templates/remediation.html"
    ).read_text()

    required = (
        "Scheduled Remediation",
        "remediation-schedule-create",
        "remediation-schedule-time",
        "remediation-schedule-cancel",
        "remediation_schedule_summary",
        "remediation_schedule_map",
        "schedule_status",
    )

    for value in required:
        assert value in content


def test_browser_converts_local_schedule_time_to_iso():
    content = Path(
        "static/js/dashboard.js"
    ).read_text()

    assert (
        "Phase 13.3 — Remediation Scheduling"
        in content
    )

    assert (
        "localDate.toISOString()"
        in content
    )

    assert (
        "/api/remediation/schedules?"
        in content
    )

    assert (
        "/cancel"
        in content
    )
