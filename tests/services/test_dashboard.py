from himp.services.dashboard import DashboardService


class FakePluginService:
    def all(self):
        return []

    def summary(self):
        return {}


class FakeExecutionService:
    def latest(self, plugin_id):
        return None

    def history(self, limit):
        return []


class FakeInventoryService:
    def summary(self):
        return type(
            "InventorySummary",
            (),
            {
                "total_hosts": 0,
                "groups": 0,
                "statistics": type(
                    "Statistics",
                    (),
                    {
                        "group_counts": [],
                    },
                )(),
                "hosts": [],
            },
        )()

    def changes(self, limit=10):
        return []


class FakeHealthService:
    def summary(self):
        return type(
            "HealthSummary",
            (),
            {
                "score": 0,
                "passed": 0,
                "warnings": 0,
                "failed": 0,
                "unknown": 0,
                "plugins": [],
            },
        )()


class FakeHealthTrendsService:
    def summary(self):
        return {}


class FakeHealthCardsService:
    def summary(self):
        return {}


class FakeHostHealthDashboardService:
    def summary(self):
        return {}


class FakeWorkflowService:
    def list_workflows(self):
        return [
            {
                "id": 1,
                "name": "Infrastructure Refresh",
                "description": "Refresh infrastructure data",
                "enabled": 1,
            },
            {
                "id": 2,
                "name": "Health Check",
                "description": "Run infrastructure health checks",
                "enabled": 1,
            },
        ]


class FakeWorkflowHistoryService:
    def __init__(self):
        self.calls = []

    def history(self, workflow_id, limit=1):
        self.calls.append((workflow_id, limit))

        histories = {
            1: [
                {
                    "workflow_execution_id": "workflow-run-001",
                    "workflow": {
                        "id": 1,
                        "name": "Infrastructure Refresh",
                    },
                    "started_at": "2026-08-15T01:00:00+00:00",
                    "completed_at": None,
                    "success": None,
                    "current_task_id": "generate_reports",
                    "executions": [],
                },
            ],
            2: [],
        }

        return histories.get(workflow_id, [])[:limit]


def make_dashboard():
    dashboard = DashboardService()

    dashboard.plugins = FakePluginService()
    dashboard.execution = FakeExecutionService()
    dashboard.inventory = FakeInventoryService()
    dashboard.health = FakeHealthService()
    dashboard.health_trends = FakeHealthTrendsService()
    dashboard.health_cards = FakeHealthCardsService()
    dashboard.host_health = FakeHostHealthDashboardService()
    dashboard.workflows = FakeWorkflowService()
    dashboard.workflow_history = FakeWorkflowHistoryService()

    return dashboard


def test_workflow_summary_exposes_latest_workflow_execution_state():
    dashboard = make_dashboard()

    result = dashboard.workflow_summary()

    assert result == [
        {
            "id": 1,
            "name": "Infrastructure Refresh",
            "description": "Refresh infrastructure data",
            "enabled": 1,
            "status": "RUNNING",
            "current_task_id": "generate_reports",
            "workflow_execution_id": "workflow-run-001",
            "started_at": "2026-08-15T01:00:00+00:00",
            "completed_at": None,
            "success": None,
        },
        {
            "id": 2,
            "name": "Health Check",
            "description": "Run infrastructure health checks",
            "enabled": 1,
            "status": "NEVER_RUN",
            "current_task_id": None,
            "workflow_execution_id": None,
            "started_at": None,
            "completed_at": None,
            "success": None,
        },
    ]


def test_workflow_summary_requests_only_latest_history():
    dashboard = make_dashboard()

    dashboard.workflow_summary()

    assert dashboard.workflow_history.calls == [
        (1, 1),
        (2, 1),
    ]


class FakeRemediationAuditRepository:
    def summary(self):
        return {
            "total": 12,
            "allow_count": 7,
            "deny_count": 2,
            "confirmation_required_count": 1,
            "execution_success_count": 6,
            "execution_failure_count": 1,
        }


class FakeSchedulerService:
    def all(self):
        return [
            {
                "task_id": "inventory_refresh",
                "name": "Inventory Refresh",
                "description": "Refresh inventory data.",
                "enabled": 1,
                "frequency": "daily",
                "schedule_time": "03:00",
                "day_of_week": None,
                "day_of_month": None,
                "last_run": "2026-08-14 03:00:00",
            },
            {
                "task_id": "health_check",
                "name": "Health Check",
                "description": "Run health validation across plugins.",
                "enabled": 0,
                "frequency": "manual",
                "schedule_time": None,
                "day_of_week": None,
                "day_of_month": None,
                "last_run": None,
            },
        ]

    def execution_status(self, task_id):
        statuses = {
            "inventory_refresh": {
                "next_run": "2026-08-16T03:00:00",
                "last_execution": {
                    "id": 10,
                    "task_id": "inventory_refresh",
                    "success": True,
                    "elapsed": 12.5,
                },
                "last_execution_success": True,
                "last_execution_at": "2026-08-15 03:00:12",
                "last_execution_elapsed": 12.5,
                "last_execution_error": None,
            },
            "health_check": {
                "next_run": None,
                "last_execution": None,
                "last_execution_success": None,
                "last_execution_at": None,
                "last_execution_elapsed": None,
                "last_execution_error": None,
            },
        }

        return statuses[task_id]


def test_remediation_summary_exposes_audit_summary():
    dashboard = make_dashboard()
    dashboard.remediation_audit = FakeRemediationAuditRepository()

    assert dashboard.remediation_summary() == {
        "total": 12,
        "allow_count": 7,
        "deny_count": 2,
        "confirmation_required_count": 1,
        "execution_success_count": 6,
        "execution_failure_count": 1,
    }


def test_automation_summary_exposes_schedule_and_execution_state():
    dashboard = make_dashboard()
    dashboard.scheduler = FakeSchedulerService()

    result = dashboard.automation_summary()

    assert result == [
        {
            "task_id": "inventory_refresh",
            "name": "Inventory Refresh",
            "description": "Refresh inventory data.",
            "enabled": True,
            "frequency": "daily",
            "schedule_time": "03:00",
            "day_of_week": None,
            "day_of_month": None,
            "last_run": "2026-08-14 03:00:00",
            "next_run": "2026-08-16T03:00:00",
            "last_execution": {
                "id": 10,
                "task_id": "inventory_refresh",
                "success": True,
                "elapsed": 12.5,
            },
            "last_execution_success": True,
            "last_execution_at": "2026-08-15 03:00:12",
            "last_execution_elapsed": 12.5,
            "last_execution_error": None,
        },
        {
            "task_id": "health_check",
            "name": "Health Check",
            "description": "Run health validation across plugins.",
            "enabled": False,
            "frequency": "manual",
            "schedule_time": None,
            "day_of_week": None,
            "day_of_month": None,
            "last_run": None,
            "next_run": None,
            "last_execution": None,
            "last_execution_success": None,
            "last_execution_at": None,
            "last_execution_elapsed": None,
            "last_execution_error": None,
        },
    ]


def test_summary_exposes_remediation():
    dashboard = make_dashboard()
    dashboard.remediation_audit = FakeRemediationAuditRepository()

    result = dashboard.summary()

    assert result["remediation"] == (
        dashboard.remediation_summary()
    )


def test_summary_exposes_workflows():
    dashboard = make_dashboard()

    result = dashboard.summary()

    assert result["workflows"] == (
        dashboard.workflow_summary()
    )

    assert result["automations"] == (
        dashboard.automation_summary()
    )
