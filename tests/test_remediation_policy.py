import pytest

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
            raise RuntimeError(
                "automation disabled"
            )

        if (
            self.task["risk_level"] == "destructive"
            and not confirmed
        ):
            raise RuntimeError(
                "confirmation required"
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
        "automation disabled"
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
