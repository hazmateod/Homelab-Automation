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
