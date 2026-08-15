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


class FakeOperationalHostHealthService:
    def __init__(
        self,
        score=100,
        passed=3,
        warnings=0,
        failed=0,
        unknown=0,
    ):
        self._summary = {
            "score": score,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "unknown": unknown,
        }

    def summary(self):
        return self._summary


class FakeOperationalRemediationAuditRepository:
    def __init__(
        self,
        total=0,
        allow_count=0,
        deny_count=0,
        confirmation_required_count=0,
        execution_success_count=0,
        execution_failure_count=0,
    ):
        self._summary = {
            "total": total,
            "allow_count": allow_count,
            "deny_count": deny_count,
            "confirmation_required_count": confirmation_required_count,
            "execution_success_count": execution_success_count,
            "execution_failure_count": execution_failure_count,
        }

    def summary(self):
        return self._summary


def test_operational_summary_reports_pass_when_all_systems_are_healthy():
    dashboard = make_dashboard()

    dashboard.host_health = FakeOperationalHostHealthService()
    dashboard.scheduler = FakeSchedulerService()
    dashboard.remediation_audit = (
        FakeOperationalRemediationAuditRepository()
    )

    result = dashboard.operational_summary()

    assert result["status"] == "PASS"

    assert result["health"] == {
        "score": 100,
        "passed": 3,
        "warnings": 0,
        "failed": 0,
        "unknown": 0,
    }

    assert result["workflows"] == {
        "total": 2,
        "running": 1,
        "failed": 0,
        "never_run": 1,
    }

    assert result["automations"]["total"] == 2
    assert result["automations"]["enabled"] == 1
    assert result["automations"]["failed"] == 0

    assert result["remediation"]["execution_failure_count"] == 0


def test_operational_summary_reports_fail_for_host_health_failure():
    dashboard = make_dashboard()

    dashboard.host_health = FakeOperationalHostHealthService(
        score=75,
        passed=2,
        failed=1,
    )

    result = dashboard.operational_summary()

    assert result["status"] == "FAIL"
    assert result["health"]["failed"] == 1


def test_operational_summary_reports_fail_for_workflow_failure():
    dashboard = make_dashboard()

    dashboard.workflows.list_workflows = lambda: [
        {
            "id": 1,
            "name": "Failed Workflow",
            "description": "Failed workflow",
            "enabled": 1,
        },
    ]

    dashboard.workflow_history.history = lambda workflow_id, limit=1: [
        {
            "workflow_execution_id": "workflow-run-failed",
            "workflow": {
                "id": 1,
                "name": "Failed Workflow",
            },
            "started_at": "2026-08-15T01:00:00+00:00",
            "completed_at": "2026-08-15T01:01:00+00:00",
            "success": False,
            "current_task_id": None,
            "executions": [],
        },
    ]

    result = dashboard.operational_summary()

    assert result["status"] == "FAIL"
    assert result["workflows"]["failed"] == 1


def test_operational_summary_reports_fail_for_automation_execution_failure():
    dashboard = make_dashboard()

    class FailedAutomationSchedulerService:
        def all(self):
            return [
                {
                    "task_id": "failed_task",
                    "name": "Failed Task",
                    "description": "Failed automation",
                    "enabled": 1,
                    "frequency": "daily",
                    "schedule_time": "03:00",
                    "day_of_week": None,
                    "day_of_month": None,
                    "last_run": "2026-08-15 03:00:00",
                },
            ]

        def execution_status(self, task_id):
            return {
                "next_run": None,
                "last_execution": {
                    "id": 99,
                    "task_id": "failed_task",
                    "success": False,
                    "elapsed": 12.5,
                },
                "last_execution_success": False,
                "last_execution_at": "2026-08-15 03:00:12",
                "last_execution_elapsed": 12.5,
                "last_execution_error": "Automation failed.",
            }

    dashboard.scheduler = FailedAutomationSchedulerService()

    result = dashboard.operational_summary()

    assert result["status"] == "FAIL"
    assert result["automations"]["failed"] == 1


def test_operational_summary_reports_fail_for_remediation_execution_failure():
    dashboard = make_dashboard()

    dashboard.remediation_audit = (
        FakeOperationalRemediationAuditRepository(
            total=1,
            allow_count=1,
            execution_failure_count=1,
        )
    )

    result = dashboard.operational_summary()

    assert result["status"] == "FAIL"
    assert result["remediation"]["execution_failure_count"] == 1


def test_operational_summary_reports_warning_for_warning_only_conditions():
    dashboard = make_dashboard()
    dashboard.scheduler = FakeSchedulerService()

    dashboard.host_health = FakeOperationalHostHealthService(
        score=90,
        passed=2,
        warnings=1,
    )

    result = dashboard.operational_summary()

    assert result["status"] == "WARNING"
    assert result["health"]["warnings"] == 1


def test_operational_summary_reports_warning_for_confirmation_required():
    dashboard = make_dashboard()
    dashboard.scheduler = FakeSchedulerService()

    dashboard.remediation_audit = (
        FakeOperationalRemediationAuditRepository(
            total=1,
            confirmation_required_count=1,
        )
    )

    result = dashboard.operational_summary()

    assert result["status"] == "WARNING"
    assert result["remediation"]["confirmation_required_count"] == 1


def test_recent_activity_exposes_plugin_execution_history():
    dashboard = make_dashboard()

    class ActivityExecutionService:
        def history(self, limit):
            assert limit == 10

            return [
                {
                    "id": 20,
                    "plugin": "detail",
                    "plugin_name": "Detail",
                    "success": 0,
                    "return_code": 1,
                    "elapsed": 0.0,
                    "executed_at": "2026-08-09T23:36:03",
                },
                {
                    "id": 19,
                    "plugin": "media",
                    "plugin_name": "Media Services",
                    "success": 1,
                    "return_code": 0,
                    "elapsed": 13.369,
                    "executed_at": "2026-08-08T17:31:23",
                },
            ]

    dashboard.execution = ActivityExecutionService()

    assert dashboard.recent_activity() == [
        {
            "category": "Plugin",
            "name": "Detail",
            "status": "FAIL",
            "timestamp": "2026-08-09T23:36:03",
            "elapsed": 0.0,
            "href": "/plugins/detail",
        },
        {
            "category": "Plugin",
            "name": "Media Services",
            "status": "SUCCESS",
            "timestamp": "2026-08-08T17:31:23",
            "elapsed": 13.369,
            "href": "/plugins/media",
        },
    ]


def test_operational_summary_exposes_attention_items():
    dashboard = make_dashboard()

    dashboard.scheduler = FakeSchedulerService()

    dashboard.host_health = FakeOperationalHostHealthService(
        score=75,
        passed=2,
        warnings=1,
        failed=1,
    )

    dashboard.remediation_audit = (
        FakeOperationalRemediationAuditRepository(
            confirmation_required_count=1,
            execution_failure_count=1,
        )
    )

    dashboard.workflows.list_workflows = lambda: [
        {
            "id": 1,
            "name": "Failed Workflow",
            "description": "Failed workflow",
            "enabled": 1,
        },
    ]

    dashboard.workflow_history.history = lambda workflow_id, limit=1: [
        {
            "workflow_execution_id": "workflow-run-failed",
            "workflow": {
                "id": 1,
                "name": "Failed Workflow",
            },
            "started_at": "2026-08-15T01:00:00+00:00",
            "completed_at": "2026-08-15T01:01:00+00:00",
            "success": False,
            "current_task_id": None,
            "executions": [],
        },
    ]

    result = dashboard.operational_summary()

    assert result["status"] == "FAIL"

    assert [
        item["category"]
        for item in result["attention"]
    ] == [
        "Infrastructure",
        "Infrastructure",
        "Workflow",
        "Remediation",
        "Remediation",
    ]


def test_summary_exposes_operational_dashboard_data():
    dashboard = make_dashboard()

    dashboard.scheduler = FakeSchedulerService()
    dashboard.remediation_audit = FakeOperationalRemediationAuditRepository()

    result = dashboard.summary()

    assert "operational" in result
    assert result["operational"]["status"] == "PASS"
    assert "attention" in result["operational"]
    assert "recent_activity" in result
