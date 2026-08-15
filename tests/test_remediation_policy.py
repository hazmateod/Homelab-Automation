import pytest

from himp.services.automation import (
    AutomationConfirmationRequiredError,
    AutomationDisabledError,
)
from himp.services.remediation_policy import (
    RemediationPolicyService,
)


class FakeAutomation:
    def __init__(
        self,
        enabled=True,
        risk_level="maintenance",
    ):
        self.task = {
            "id": "scheduled_updates",
            "name": "Scheduled Updates",
            "enabled": enabled,
            "risk_level": risk_level,
        }

    def find_task(
        self,
        task_id,
    ):
        assert task_id == "scheduled_updates"
        return self.task

    def validate_execution_policy(
        self,
        task_id,
        confirmed=False,
    ):
        if not self.task["enabled"]:
            raise AutomationDisabledError(
                f"Automation task is disabled: {task_id}"
            )

        if (
            self.task["risk_level"] == "destructive"
            and not confirmed
        ):
            raise AutomationConfirmationRequiredError(
                "Destructive automation requires explicit confirmation: "
                f"{task_id}"
            )

        return {
            "task_id": task_id,
            "enabled": self.task["enabled"],
            "risk_level": self.task["risk_level"],
            "confirmed": confirmed,
        }


def make_service(
    automation=None,
):
    return RemediationPolicyService(
        automation=(
            automation
            or FakeAutomation()
        )
    )


def proposal(
    task_id="scheduled_updates",
    reason="Host health indicates maintenance is required.",
    evidence=None,
):
    return {
        "task_id": task_id,
        "reason": reason,
        "evidence": (
            evidence
            or {
                "hostname": "pve01",
                "status": "WARNING",
            }
        ),
    }


def test_safe_maintenance_remediation_is_allowed():
    service = make_service()

    result = service.evaluate(
        proposal()
    )

    assert result == {
        "decision": "ALLOW",
        "task_id": "scheduled_updates",
        "reason": (
            "Host health indicates maintenance is required."
        ),
        "evidence": {
            "hostname": "pve01",
            "status": "WARNING",
        },
        "risk_level": "maintenance",
        "confirmation_required": False,
    }


def test_disabled_automation_is_denied():
    service = make_service(
        FakeAutomation(
            enabled=False
        )
    )

    result = service.evaluate(
        proposal()
    )

    assert result["decision"] == "DENY"
    assert result["task_id"] == "scheduled_updates"
    assert result["reason"] == (
        "Automation task is disabled: scheduled_updates"
    )


def test_destructive_remediation_requires_confirmation():
    service = make_service(
        FakeAutomation(
            risk_level="destructive"
        )
    )

    result = service.evaluate(
        proposal()
    )

    assert result["decision"] == (
        "CONFIRM_REQUIRED"
    )
    assert result["task_id"] == "scheduled_updates"
    assert result["risk_level"] == "destructive"
    assert result["confirmation_required"] is True


def test_destructive_remediation_with_confirmation_is_allowed():
    service = make_service(
        FakeAutomation(
            risk_level="destructive"
        )
    )

    result = service.evaluate(
        proposal(),
        confirmed=True,
    )

    assert result["decision"] == "ALLOW"
    assert result["task_id"] == "scheduled_updates"
    assert result["risk_level"] == "destructive"
    assert result["confirmation_required"] is False


def test_missing_task_is_rejected():
    class MissingAutomation(FakeAutomation):
        def find_task(
            self,
            task_id,
        ):
            raise ValueError(
                f"Automation task does not exist: {task_id}"
            )

    service = make_service(
        MissingAutomation()
    )

    with pytest.raises(
        ValueError,
        match="Automation task does not exist",
    ):
        service.evaluate(
            proposal()
        )


def test_policy_does_not_execute_automation():
    class RecordingAutomation(FakeAutomation):
        def __init__(self):
            super().__init__()
            self.run_calls = []

        def run(
            self,
            *args,
            **kwargs,
        ):
            self.run_calls.append(
                (args, kwargs)
            )

    automation = RecordingAutomation()
    service = make_service(
        automation
    )

    result = service.evaluate(
        proposal()
    )

    assert result["decision"] == "ALLOW"
    assert automation.run_calls == []


def test_unexpected_policy_error_is_not_converted_to_denial():
    class BrokenAutomation(FakeAutomation):
        def validate_execution_policy(
            self,
            task_id,
            confirmed=False,
        ):
            raise RuntimeError(
                "unexpected policy failure"
            )

    service = make_service(
        BrokenAutomation()
    )

    with pytest.raises(
        RuntimeError,
        match="unexpected policy failure",
    ):
        service.evaluate(
            proposal()
        )


def test_dependency_policy_error_is_not_converted_to_allow():
    from himp.services.automation import (
        AutomationDependencyNotSatisfiedError,
    )

    class DependencyFailureAutomation(FakeAutomation):
        def validate_execution_policy(
            self,
            task_id,
            confirmed=False,
        ):
            raise AutomationDependencyNotSatisfiedError(
                f"Dependency failed for {task_id}"
            )

    service = make_service(
        DependencyFailureAutomation()
    )

    with pytest.raises(
        AutomationDependencyNotSatisfiedError,
        match="Dependency failed for scheduled_updates",
    ):
        service.evaluate(
            proposal()
        )


def test_confirmation_cannot_override_disabled_automation():
    service = make_service(
        FakeAutomation(
            enabled=False,
            risk_level="destructive",
        )
    )

    result = service.evaluate(
        proposal(),
        confirmed=True,
    )

    assert result["decision"] == "DENY"
    assert result["confirmation_required"] is False
    assert result["risk_level"] == "destructive"
