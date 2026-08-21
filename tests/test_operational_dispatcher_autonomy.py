from himp.services.operational_dispatcher import (
    OperationalDispatcher,
)


class FakeAutomation:
    def __init__(self):
        self.run_calls = []

    def run(
        self,
        task_id,
    ):
        self.run_calls.append(
            task_id
        )

        return {
            "task":
                task_id,
            "success":
                True,
        }


class FakeOperations:
    def __init__(
        self,
        configuration,
    ):
        self.configuration = (
            configuration
        )

    def get(self):
        return self.configuration


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
                "source_type":
                    source_type,
                "source_id":
                    source_id,
                "baseline":
                    baseline,
                "change_limit":
                    change_limit,
            }
        )

        return {
            "source_type":
                source_type,
            "source_id":
                source_id,
            "recommendation_count":
                1,
            "automatic_eligible_count":
                0,
            "executed_count":
                0,
            "approval_required_count":
                1,
            "denied_count":
                0,
            "execution_performed":
                False,
            "results":
                [],
        }


class ExplodingLegacyWorkflow:
    def run(
        self,
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "legacy remediation workflow "
            "must not execute"
        )


def configuration(
    enabled=True,
):
    return {
        "enabled":
            enabled,
        "source_type":
            "application",
        "source_id":
            "himp",
        "baseline":
            None,
        "change_limit":
            10,
    }


def test_remediation_operations_use_autonomous_workflow():
    automation = FakeAutomation()

    workflow = (
        FakeAutonomousWorkflow()
    )

    dispatcher = OperationalDispatcher(
        automation=automation,
        remediation_operations=(
            FakeOperations(
                configuration()
            )
        ),
        remediation_workflow=(
            ExplodingLegacyWorkflow()
        ),
        remediation_autonomous_workflow=
            workflow,
    )

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["success"] is True

    assert result["result"][
        "execution_performed"
    ] is False

    assert workflow.calls == [
        {
            "source_type":
                "application",
            "source_id":
                "himp",
            "baseline":
                None,
            "change_limit":
                10,
        }
    ]

    assert automation.run_calls == []


def test_disabled_remediation_operations_do_not_run_autonomy():
    workflow = (
        FakeAutonomousWorkflow()
    )

    dispatcher = OperationalDispatcher(
        automation=FakeAutomation(),
        remediation_operations=(
            FakeOperations(
                configuration(
                    enabled=False
                )
            )
        ),
        remediation_autonomous_workflow=
            workflow,
    )

    result = dispatcher.dispatch(
        "remediation_operations"
    )

    assert result["skipped"] is True
    assert workflow.calls == []
