from himp.services.application_health import (
    ApplicationHealthService,
)


class FakeDatabase:
    def query(self, sql, parameters=()):
        return [{"ok": 1}]


class FakeScheduler:
    def all(self):
        return [
            {
                "task_id": "health_check",
                "enabled": 1,
            },
            {
                "task_id": "scheduled_updates",
                "enabled": 1,
            },
        ]


class FakeAutomation:
    def summary(self):
        return {
            "tasks": 5,
            "enabled": 4,
            "disabled": 1,
            "automation": [],
        }


class FakeSettings:
    def paths(self):
        return {
            "inventory": {
                "path": "inventory/hosts.yml",
                "exists": True,
            },
            "dashboard": {
                "path": "reports/dashboard/dashboard.json",
                "exists": True,
            },
            "maintenance_playbook": {
                "path": "playbooks/maintenance.yml",
                "exists": True,
            },
            "report_playbook": {
                "path": "playbooks/generate_reports.yml",
                "exists": True,
            },
            "dashboard_playbook": {
                "path": "playbooks/dashboard.yml",
                "exists": True,
            },
        }


def test_application_health_reports_healthy_components(
    monkeypatch,
):
    service = ApplicationHealthService()

    service.database = FakeDatabase()
    service.scheduler = FakeScheduler()
    service.automation = FakeAutomation()
    service.settings = FakeSettings()

    monkeypatch.setattr(
        service,
        "_storage",
        lambda: {
            "status": "healthy",
            "details": {
                "data": True,
                "reports": True,
            },
        },
    )

    result = service.summary()

    assert result["status"] == "healthy"

    assert result["components"]["database"]["status"] == "healthy"
    assert result["components"]["scheduler"]["status"] == "healthy"
    assert result["components"]["automation"]["status"] == "healthy"
    assert result["components"]["configuration"]["status"] == "healthy"
    assert result["components"]["storage"]["status"] == "healthy"


def test_application_health_reports_database_failure():
    service = ApplicationHealthService()

    class BrokenDatabase:
        def query(self, sql, parameters=()):
            raise RuntimeError("database unavailable")

    service.database = BrokenDatabase()

    result = service.summary()

    assert result["status"] == "critical"
    assert result["components"]["database"]["status"] == "critical"
    assert "database unavailable" in result["components"]["database"]["message"]


def test_application_health_reports_scheduler_failure():
    service = ApplicationHealthService()

    class BrokenScheduler:
        def all(self):
            raise RuntimeError("scheduler unavailable")

    service.scheduler = BrokenScheduler()

    result = service.summary()

    assert result["status"] == "critical"
    assert result["components"]["scheduler"]["status"] == "critical"
    assert "scheduler unavailable" in result["components"]["scheduler"]["message"]


def test_application_health_reports_automation_failure():
    service = ApplicationHealthService()

    class BrokenAutomation:
        def summary(self):
            raise RuntimeError("automation unavailable")

    service.automation = BrokenAutomation()

    result = service.summary()

    assert result["status"] == "critical"
    assert result["components"]["automation"]["status"] == "critical"
    assert "automation unavailable" in result["components"]["automation"]["message"]


def test_application_health_reports_configuration_failure():
    service = ApplicationHealthService()

    class BrokenSettings:
        def paths(self):
            return {
                "inventory": {
                    "path": "inventory/hosts.yml",
                    "exists": False,
                },
            }

    service.settings = BrokenSettings()

    result = service.summary()

    assert result["status"] == "warning"
    assert result["components"]["configuration"]["status"] == "warning"


def test_application_health_reports_storage_failure(
    monkeypatch,
):
    service = ApplicationHealthService()

    monkeypatch.setattr(
        service,
        "_storage",
        lambda: {
            "status": "critical",
            "details": {
                "data": False,
                "reports": True,
            },
        },
    )

    result = service.summary()

    assert result["status"] == "critical"
    assert result["components"]["storage"]["status"] == "critical"


class FakeOperationsScheduler:
    def __init__(self, fail=False):
        self.fail = fail

    def all(self):
        if self.fail:
            raise RuntimeError("scheduler unavailable")

        return [
            {
                "task_id": "health_check",
                "name": "Health Check",
                "enabled": True,
                "frequency": "hourly",
            },
            {
                "task_id": "scheduled_updates",
                "name": "Scheduled Updates",
                "enabled": False,
                "frequency": "manual",
            },
        ]

    def execution_status(self, task_id):
        if task_id == "health_check":
            return {
                "next_run": "2026-08-28T01:00:00",
                "last_execution_success": True,
                "last_execution_at": "2026-08-28T00:00:00",
                "last_execution_elapsed": 1.25,
                "last_execution_error": None,
            }

        return {
            "next_run": None,
            "last_execution_success": False,
            "last_execution_at": "2026-08-27T23:00:00",
            "last_execution_elapsed": 2.5,
            "last_execution_error": "update failed",
        }


class FakeMaintenanceWindows:
    def __init__(self, fail=False):
        self.fail = fail

    def active_all(self):
        if self.fail:
            raise RuntimeError("maintenance unavailable")

        return [
            {
                "id": 1,
                "name": "Active Maintenance",
                "reason": "Infrastructure work",
                "task_id": None,
                "starts_at": "2026-08-27T22:00:00",
                "ends_at": "2026-08-28T00:30:00",
            }
        ]

    def upcoming(self, limit=10):
        assert limit == 10

        return [
            {
                "id": 2,
                "name": "Upcoming Maintenance",
                "reason": "Patch window",
                "task_id": "scheduled_updates",
                "starts_at": "2026-08-29T01:00:00",
                "ends_at": "2026-08-29T02:00:00",
            }
        ]


class FakeHostHealthDashboard:
    def __init__(self, fail=False):
        self.fail = fail

    def summary(self):
        if self.fail:
            raise RuntimeError("host health unavailable")

        return {
            "total": 45,
            "passed": 42,
            "warnings": 1,
            "failed": 1,
            "unknown": 1,
            "score": 94,
        }


def test_application_health_exposes_release_revision(tmp_path):
    release_marker = tmp_path / ".himp-release"
    release_marker.write_text(
        "abc123\n",
        encoding="utf-8",
    )

    service = ApplicationHealthService(
        scheduler=FakeOperationsScheduler(),
        maintenance_windows=FakeMaintenanceWindows(),
        host_health=FakeHostHealthDashboard(),
        release_marker=release_marker,
    )

    release = service._release()

    assert release == {
        "revision": "abc123",
        "available": True,
    }


def test_application_health_release_is_optional(tmp_path):
    service = ApplicationHealthService(
        scheduler=FakeOperationsScheduler(),
        maintenance_windows=FakeMaintenanceWindows(),
        host_health=FakeHostHealthDashboard(),
        release_marker=tmp_path / "missing-release",
    )

    assert service._release() == {
        "revision": None,
        "available": False,
    }


def test_application_health_scheduler_operations_summary():
    service = ApplicationHealthService(
        scheduler=FakeOperationsScheduler(),
        maintenance_windows=FakeMaintenanceWindows(),
        host_health=FakeHostHealthDashboard(),
    )

    result = service._scheduler_operations()

    assert result["available"] is True
    assert result["total"] == 2
    assert result["enabled"] == 1
    assert result["disabled"] == 1
    assert result["failed"] == 1
    assert result["schedules"][0]["task_id"] == "health_check"
    assert result["schedules"][0]["next_run"] == (
        "2026-08-28T01:00:00"
    )
    assert result["schedules"][1]["last_execution_error"] == (
        "update failed"
    )


def test_application_health_maintenance_summary():
    service = ApplicationHealthService(
        scheduler=FakeOperationsScheduler(),
        maintenance_windows=FakeMaintenanceWindows(),
        host_health=FakeHostHealthDashboard(),
    )

    result = service._maintenance()

    assert result["available"] is True
    assert result["active_count"] == 1
    assert result["upcoming_count"] == 1
    assert result["active"][0]["name"] == "Active Maintenance"
    assert result["upcoming"][0]["name"] == "Upcoming Maintenance"


def test_application_health_infrastructure_summary():
    service = ApplicationHealthService(
        scheduler=FakeOperationsScheduler(),
        maintenance_windows=FakeMaintenanceWindows(),
        host_health=FakeHostHealthDashboard(),
    )

    result = service._infrastructure()

    assert result == {
        "available": True,
        "total": 45,
        "passed": 42,
        "warnings": 1,
        "failed": 1,
        "unknown": 1,
        "score": 94,
    }


def test_application_health_operations_collectors_are_failure_isolated():
    service = ApplicationHealthService(
        scheduler=FakeOperationsScheduler(
            fail=True
        ),
        maintenance_windows=FakeMaintenanceWindows(
            fail=True
        ),
        host_health=FakeHostHealthDashboard(
            fail=True
        ),
    )

    scheduler = service._scheduler_operations()
    maintenance = service._maintenance()
    infrastructure = service._infrastructure()

    assert scheduler["available"] is False
    assert scheduler["total"] == 0
    assert "scheduler unavailable" in scheduler["error"]

    assert maintenance["available"] is False
    assert maintenance["active_count"] == 0
    assert "maintenance unavailable" in maintenance["error"]

    assert infrastructure["available"] is False
    assert infrastructure["total"] == 0
    assert "host health unavailable" in infrastructure["error"]
