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

    service.automation_executions = (
        FakeAutomationExecutionRepository()
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
        "executions": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "recent": [],
        },
    }


def test_operational_summary_handles_missing_dashboard():
    service = ReportService()

    service.root = service.root / "missing-phase-9-2-test"

    service.automation_executions = (
        FakeAutomationExecutionRepository()
    )

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
        "executions": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "recent": [],
        },
    }


class FakeAutomationExecutionRepository:
    def __init__(self, history=None):
        self._history = history or []

    def history(self, limit=50):
        return self._history[:limit]


def test_operational_summary_includes_execution_history(
    tmp_path,
    monkeypatch,
):
    service = ReportService()

    service.root = tmp_path / "reports"

    monkeypatch.setattr(
        service,
        "dashboard",
        lambda: None,
    )

    service.automation_executions = (
        FakeAutomationExecutionRepository(
            [
                {
                    "id": 3,
                    "task_id": "scheduled_updates",
                    "success": True,
                    "elapsed": 12.5,
                    "result": {
                        "changed": 4,
                    },
                    "executed_at": "2026-08-15 14:00:00",
                },
                {
                    "id": 2,
                    "task_id": "generate_reports",
                    "success": False,
                    "elapsed": 4.25,
                    "result": {
                        "error": "timeout",
                    },
                    "executed_at": "2026-08-15 13:00:00",
                },
            ]
        )
    )

    result = service.operational_summary()

    assert result["executions"] == {
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


def test_operational_summary_handles_no_execution_history(
    tmp_path,
    monkeypatch,
):
    service = ReportService()

    service.root = tmp_path / "reports"

    monkeypatch.setattr(
        service,
        "dashboard",
        lambda: None,
    )

    service.automation_executions = (
        FakeAutomationExecutionRepository()
    )

    result = service.operational_summary()

    assert result["executions"] == {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "recent": [],
    }
