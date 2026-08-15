from himp.services.logs import LogService


class FakeAutomationExecutions:

    def history(self, limit=100):
        return [
            {
                "id": 3,
                "task_id": "scheduled_updates",
                "workflow_execution_id": None,
                "success": True,
                "elapsed": 12.5,
                "result": {"message": "complete"},
                "executed_at": "2026-08-15 14:00:00",
            }
        ]


class FakeWorkflowExecutions:

    def history(self, limit=100):
        return [
            {
                "id": 2,
                "workflow_id": 7,
                "workflow_execution_id": "wf-001",
                "started_at": "2026-08-15 13:59:00",
                "completed_at": "2026-08-15 13:59:30",
                "success": True,
                "current_task_id": None,
            }
        ]


class FakeExecutions:

    def history(self, limit=100):
        return [
            {
                "id": 1,
                "plugin": "health",
                "success": False,
                "return_code": 1,
                "elapsed": 2.5,
                "stdout": "stdout",
                "stderr": "stderr",
                "warnings": ["warning"],
                "artifacts": {"report": "health.json"},
                "created_at": "2026-08-15 13:58:00",
            }
        ]


class FakeRemediationAudit:

    def history(self, limit=100):
        return [
            {
                "id": 4,
                "source_type": "host_health",
                "source_id": "pve01",
                "task_id": "restart_service",
                "decision": "CONFIRM_REQUIRED",
                "reason": "service unhealthy",
                "evidence": {"service": "pveproxy"},
                "risk_level": "medium",
                "confirmation_required": True,
                "confirmed": False,
                "execution_id": None,
                "execution_success": None,
                "created_at": "2026-08-15 14:01:00",
            }
        ]


def test_log_service_normalizes_all_existing_sources():
    service = LogService(
        automation_executions=FakeAutomationExecutions(),
        workflow_executions=FakeWorkflowExecutions(),
        executions=FakeExecutions(),
        remediation_audit=FakeRemediationAudit(),
    )

    records = service.history()

    assert len(records) == 4
    assert {
        record["source"]
        for record in records
    } == {
        "automation",
        "workflow",
        "plugin",
        "remediation",
    }


def test_log_service_returns_common_record_shape():
    service = LogService(
        automation_executions=FakeAutomationExecutions(),
        workflow_executions=FakeWorkflowExecutions(),
        executions=FakeExecutions(),
        remediation_audit=FakeRemediationAudit(),
    )

    records = service.history()

    for record in records:
        assert set(record) == {
            "id",
            "timestamp",
            "source",
            "event",
            "status",
            "message",
            "details",
        }


def test_log_service_orders_records_by_timestamp():
    service = LogService(
        automation_executions=FakeAutomationExecutions(),
        workflow_executions=FakeWorkflowExecutions(),
        executions=FakeExecutions(),
        remediation_audit=FakeRemediationAudit(),
    )

    records = service.history()

    assert [
        record["source"]
        for record in records
    ] == [
        "remediation",
        "automation",
        "workflow",
        "plugin",
    ]


def test_log_service_normalizes_workflow_running_state():
    class RunningWorkflowExecutions:

        def history(self, limit=100):
            return [
                {
                    "workflow_id": 7,
                    "workflow_execution_id": "wf-running",
                    "started_at": "2026-08-15 15:00:00",
                    "completed_at": None,
                    "success": None,
                    "current_task_id": "health_check",
                }
            ]

    service = LogService(
        automation_executions=FakeAutomationExecutions(),
        workflow_executions=RunningWorkflowExecutions(),
        executions=FakeExecutions(),
        remediation_audit=FakeRemediationAudit(),
    )

    workflow = next(
        record
        for record in service.history()
        if record["source"] == "workflow"
    )

    assert workflow["status"] == "running"
    assert workflow["details"]["current_task_id"] == (
        "health_check"
    )


def test_log_service_preserves_execution_details():
    service = LogService(
        automation_executions=FakeAutomationExecutions(),
        workflow_executions=FakeWorkflowExecutions(),
        executions=FakeExecutions(),
        remediation_audit=FakeRemediationAudit(),
    )

    plugin = next(
        record
        for record in service.history()
        if record["source"] == "plugin"
    )

    assert plugin["details"]["stdout"] == "stdout"
    assert plugin["details"]["stderr"] == "stderr"
    assert plugin["details"]["warnings"] == ["warning"]
    assert plugin["details"]["artifacts"] == {
        "report": "health.json"
    }


def test_log_service_sorts_mixed_naive_and_aware_datetimes():
    from datetime import datetime, timezone

    class MixedAutomationExecutions:
        def history(self, limit=100):
            return [
                {
                    "id": 1,
                    "task_id": "naive",
                    "workflow_execution_id": None,
                    "success": True,
                    "elapsed": 1.0,
                    "result": {},
                    "executed_at": datetime(
                        2026,
                        8,
                        15,
                        14,
                        0,
                    ),
                },
                {
                    "id": 2,
                    "task_id": "aware",
                    "workflow_execution_id": None,
                    "success": True,
                    "elapsed": 1.0,
                    "result": {},
                    "executed_at": datetime(
                        2026,
                        8,
                        15,
                        14,
                        1,
                        tzinfo=timezone.utc,
                    ),
                },
            ]

    class EmptyHistory:
        def history(self, limit=100):
            return []

    service = LogService(
        automation_executions=MixedAutomationExecutions(),
        workflow_executions=EmptyHistory(),
        executions=EmptyHistory(),
        remediation_audit=EmptyHistory(),
    )

    records = service.history(500)

    assert len(records) == 2
    assert records[0]["id"] == "automation:2"
    assert records[1]["id"] == "automation:1"


def test_log_service_handles_large_history_limit_with_mixed_timestamps():
    from datetime import datetime, timezone

    class MixedHistory:
        def history(self, limit=100):
            return [
                {
                    "id": 1,
                    "task_id": "naive",
                    "workflow_execution_id": None,
                    "success": True,
                    "elapsed": 1.0,
                    "result": {},
                    "executed_at": datetime(
                        2026,
                        8,
                        15,
                        14,
                        0,
                    ),
                },
                {
                    "id": 2,
                    "task_id": "aware",
                    "workflow_execution_id": None,
                    "success": True,
                    "elapsed": 1.0,
                    "result": {},
                    "executed_at": datetime(
                        2026,
                        8,
                        15,
                        14,
                        1,
                        tzinfo=timezone.utc,
                    ),
                },
            ]

    class EmptyHistory:
        def history(self, limit=100):
            return []

    service = LogService(
        automation_executions=MixedHistory(),
        workflow_executions=EmptyHistory(),
        executions=EmptyHistory(),
        remediation_audit=EmptyHistory(),
    )

    for limit in (100, 500, 1000, 5000):
        records = service.history(limit)
        assert len(records) == 2
