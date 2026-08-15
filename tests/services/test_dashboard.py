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


def test_summary_exposes_workflows():
    dashboard = make_dashboard()

    result = dashboard.summary()

    assert result["workflows"] == (
        dashboard.workflow_summary()
    )
