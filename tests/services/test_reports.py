from himp.services.reports import ReportService


def test_operational_summary_exposes_dashboard_and_report_inventory(
    tmp_path,
    monkeypatch,
):
    service = ReportService()

    service.root = tmp_path / "reports"

    dashboard_dir = service.root / "dashboard"
    current_dir = service.root / "current"
    history_dir = service.root / "history"
    health_dir = service.root / "health"
    discovery_dir = service.root / "discovery"
    json_dir = service.root / "json"

    dashboard_dir.mkdir(parents=True)
    current_dir.mkdir()
    history_dir.mkdir()
    health_dir.mkdir()
    discovery_dir.mkdir()
    json_dir.mkdir()

    (dashboard_dir / "dashboard.json").write_text("{}")
    (current_dir / "host1.md").write_text("current")
    (current_dir / "host2.md").write_text("current")
    (history_dir / "host1.md").write_text("history")
    (health_dir / "health.json").write_text("{}")
    (discovery_dir / "discovery.json").write_text("{}")
    (json_dir / "host1.json").write_text("{}")

    monkeypatch.setattr(
        service,
        "dashboard",
        lambda: {
            "generated": "2026-08-15T13:43:41Z",
            "hosts": 43,
            "healthy": 3,
            "warnings": 0,
            "critical": 1,
            "unknown": 39,
            "average_score": 25.0,
        },
    )

    assert service.operational_summary() == {
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


def test_operational_summary_handles_missing_dashboard():
    service = ReportService()

    service.root = service.root / "missing-phase-9-2-test"

    assert service.operational_summary() == {
        "generated": None,
        "dashboard": None,
        "reports": {
            "current": 0,
            "history": 0,
            "health": 0,
            "discovery": 0,
            "json": 0,
        },
    }
