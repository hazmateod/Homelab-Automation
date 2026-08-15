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
    def __init__(self):
        self.calls = []

    def run(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
        confirmed=False,
    ):
        self.calls.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "baseline": baseline,
                "change_limit": change_limit,
                "confirmed": confirmed,
            }
        )

        return {
            "source_type": source_type,
            "source_id": source_id,
            "executed_count": 1,
        }


def make_dispatcher(
    configuration=None,
):
    automation = FakeAutomation()
    operations = FakeOperations(
        configuration=configuration
    )
    workflow = FakeWorkflow()

    dispatcher = OperationalDispatcher(
        automation=automation,
        remediation_operations=operations,
        remediation_workflow=workflow,
    )

    return (
        dispatcher,
        automation,
        operations,
        workflow,
    )


def test_normal_task_uses_existing_automation():
    (
        dispatcher,
        automation,
        operations,
        workflow,
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


def test_enabled_remediation_uses_existing_workflow():
    (
        dispatcher,
        automation,
        operations,
        workflow,
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
    assert result["result"]["executed_count"] == 1
    assert automation.calls == []
    assert operations.calls == [
        ("get",)
    ]
    assert workflow.calls == [
        {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": {
                "status": "WARNING",
            },
            "change_limit": 5,
            "confirmed": False,
        }
    ]


def test_disabled_remediation_does_not_execute():
    (
        dispatcher,
        automation,
        operations,
        workflow,
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
    ) = make_dispatcher()

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["success"] is False
    assert result["error_category"] == "configuration"
    assert automation.calls == []
    assert workflow.calls == []


def test_scheduled_remediation_never_confirms_automatically():
    (
        dispatcher,
        _,
        _,
        workflow,
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

    assert workflow.calls[0]["confirmed"] is False


def test_enabled_remediation_returns_scheduler_compatible_result():
    (
        dispatcher,
        _,
        _,
        _,
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
