from himp.services.operational_dispatcher import (
    OperationalDispatcher,
)


class FakeAutomation:
    def __init__(self):
        self.calls = []

    def run(self, task_id):
        self.calls.append(task_id)

        return {
            "task": task_id,
            "result": {
                "success": True,
            },
        }


class FakeOperations:
    def __init__(
        self,
        configuration=None,
    ):
        self.configuration = configuration
        self.calls = []

    def get(self):
        self.calls.append(
            ("get",)
        )

        return self.configuration


class FakeWorkflow:
    """
    Legacy remediation workflow.

    Phase 13.5 keeps this constructor seam for compatibility, but
    remediation_operations must no longer invoke it.
    """

    def __init__(self):
        self.calls = []

    def run(
        self,
        *args,
        **kwargs,
    ):
        self.calls.append(
            {
                "args": args,
                "kwargs": kwargs,
            }
        )

        raise AssertionError(
            "legacy remediation workflow "
            "must not execute"
        )


class FakeAutonomousWorkflow:
    def __init__(self):
        self.calls = []

    def run(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
    ):
        self.calls.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "baseline": baseline,
                "change_limit": change_limit,
            }
        )

        return {
            "source_type": source_type,
            "source_id": source_id,
            "baseline": baseline,
            "change_limit": change_limit,
            "recommendation_count": 1,
            "automatic_eligible_count": 0,
            "executed_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "approval_required_count": 1,
            "denied_count": 0,
            "execution_performed": False,
            "audit_ids": [],
            "results": [],
        }


def make_dispatcher(
    configuration=None,
):
    automation = FakeAutomation()
    operations = FakeOperations(
        configuration=configuration
    )
    workflow = FakeWorkflow()
    autonomous_workflow = (
        FakeAutonomousWorkflow()
    )

    dispatcher = OperationalDispatcher(
        automation=automation,
        remediation_operations=operations,
        remediation_workflow=workflow,
        remediation_autonomous_workflow=(
            autonomous_workflow
        ),
    )

    return (
        dispatcher,
        automation,
        operations,
        workflow,
        autonomous_workflow,
    )


def test_normal_task_uses_existing_automation():
    (
        dispatcher,
        automation,
        operations,
        workflow,
        autonomous_workflow,
    ) = make_dispatcher()

    result = dispatcher.dispatch(
        "health_check"
    )

    assert result["task"] == "health_check"
    assert automation.calls == [
        "health_check"
    ]
    assert operations.calls == []
    assert workflow.calls == []


def test_enabled_remediation_uses_autonomous_workflow():
    (
        dispatcher,
        automation,
        operations,
        workflow,
        autonomous_workflow,
    ) = make_dispatcher(
        configuration={
            "enabled": True,
            "source_type": "host",
            "source_id": "pve01",
            "baseline": {
                "status": "WARNING",
            },
            "change_limit": 5,
        }
    )

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["success"] is True

    assert result["result"][
        "executed_count"
    ] == 0

    assert result["result"][
        "approval_required_count"
    ] == 1

    assert result["result"][
        "execution_performed"
    ] is False

    assert automation.calls == []

    assert operations.calls == [
        ("get",)
    ]

    assert workflow.calls == []

    assert autonomous_workflow.calls == [
        {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": {
                "status": "WARNING",
            },
            "change_limit": 5,
        }
    ]


def test_disabled_remediation_does_not_execute():
    (
        dispatcher,
        automation,
        operations,
        workflow,
        autonomous_workflow,
    ) = make_dispatcher(
        configuration={
            "enabled": False,
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    )

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["success"] is True
    assert result["skipped"] is True
    assert automation.calls == []
    assert workflow.calls == []


def test_missing_remediation_configuration_fails_closed():
    (
        dispatcher,
        automation,
        operations,
        workflow,
        autonomous_workflow,
    ) = make_dispatcher()

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["success"] is False
    assert result["error_category"] == "configuration"
    assert automation.calls == []
    assert workflow.calls == []


def test_scheduled_remediation_never_uses_legacy_confirmation_path():
    (
        dispatcher,
        _,
        _,
        workflow,
        autonomous_workflow,
    ) = make_dispatcher(
        configuration={
            "enabled": True,
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    )

    dispatcher.dispatch(
        "remediation_operations"
    )

    assert workflow.calls == []

    assert autonomous_workflow.calls == [
        {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    ]


def test_enabled_remediation_returns_scheduler_compatible_result():
    (
        dispatcher,
        _,
        _,
        _,
        autonomous_workflow,
    ) = make_dispatcher(
        configuration={
            "enabled": True,
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    )

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["task"] == "remediation_operations"
    assert result["success"] is True
    assert "executed_at" in result
    assert "result" in result


def test_disabled_remediation_returns_scheduler_compatible_result():
    (
        dispatcher,
        _,
        _,
        _,
        autonomous_workflow,
    ) = make_dispatcher(
        configuration={
            "enabled": False,
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    )

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["task"] == "remediation_operations"
    assert result["success"] is True
    assert result["skipped"] is True
    assert "executed_at" in result
