import pytest

from himp.services.remediation_execution import (
    RemediationExecutionService,
)


class FakePolicy:
    def __init__(
        self,
        decision="ALLOW",
    ):
        self.decision = decision
        self.calls = []

    def evaluate(
        self,
        proposal,
        confirmed=False,
    ):
        self.calls.append(
            (
                proposal,
                confirmed,
            )
        )

        if self.decision == "DENY":
            return {
                "decision": "DENY",
                "task_id": proposal["task_id"],
                "reason": "automation disabled",
                "evidence": proposal["evidence"],
                "risk_level": "maintenance",
                "confirmation_required": False,
            }

        if self.decision == "CONFIRM_REQUIRED":
            return {
                "decision": "CONFIRM_REQUIRED",
                "task_id": proposal["task_id"],
                "reason": proposal["reason"],
                "evidence": proposal["evidence"],
                "risk_level": "destructive",
                "confirmation_required": True,
            }

        return {
            "decision": "ALLOW",
            "task_id": proposal["task_id"],
            "reason": proposal["reason"],
            "evidence": proposal["evidence"],
            "risk_level": "maintenance",
            "confirmation_required": False,
        }


class FakeAutomation:
    def __init__(self):
        self.run_calls = []

    def run(
        self,
        task_id,
        confirmed=False,
    ):
        self.run_calls.append(
            (
                task_id,
                confirmed,
            )
        )

        return {
            "id": 42,
            "task": task_id,
            "success": True,
            "result": {
                "success": True,
            },
        }


def proposal():
    return {
        "task_id": "scheduled_updates",
        "reason": "Host health indicates maintenance is required.",
        "evidence": {
            "hostname": "pve01",
            "status": "WARNING",
        },
    }


def make_service(
    decision="ALLOW",
):
    policy = FakePolicy(
        decision=decision
    )

    automation = FakeAutomation()

    service = RemediationExecutionService(
        policy=policy,
        automation=automation,
    )

    return (
        service,
        policy,
        automation,
    )


def test_allowed_remediation_executes_automation():
    service, policy, automation = make_service()

    result = service.execute(
        proposal()
    )

    assert result["decision"] == "ALLOW"
    assert result["execution"]["id"] == 42
    assert result["execution"]["success"] is True

    assert automation.run_calls == [
        (
            "scheduled_updates",
            False,
        )
    ]

    assert len(policy.calls) == 1


def test_denied_remediation_does_not_execute():
    service, policy, automation = make_service(
        decision="DENY"
    )

    result = service.execute(
        proposal()
    )

    assert result["decision"] == "DENY"
    assert "execution" not in result
    assert automation.run_calls == []


def test_confirmation_required_does_not_execute():
    service, policy, automation = make_service(
        decision="CONFIRM_REQUIRED"
    )

    result = service.execute(
        proposal()
    )

    assert result["decision"] == (
        "CONFIRM_REQUIRED"
    )
    assert result["confirmation_required"] is True
    assert "execution" not in result
    assert automation.run_calls == []


def test_confirmed_allowed_remediation_passes_confirmation():
    service, policy, automation = make_service()

    result = service.execute(
        proposal(),
        confirmed=True,
    )

    assert result["decision"] == "ALLOW"
    assert result["execution"]["success"] is True

    assert automation.run_calls == [
        (
            "scheduled_updates",
            True,
        )
    ]

    assert policy.calls[0][1] is True


def test_policy_result_is_preserved():
    service, policy, automation = make_service()

    result = service.execute(
        proposal()
    )

    assert result["policy"] == {
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


def test_automation_execution_errors_propagate():
    class FailingAutomation(FakeAutomation):
        def run(
            self,
            task_id,
            confirmed=False,
        ):
            raise RuntimeError(
                "automation execution failed"
            )

    policy = FakePolicy()
    automation = FailingAutomation()

    service = RemediationExecutionService(
        policy=policy,
        automation=automation,
    )

    with pytest.raises(
        RuntimeError,
        match="automation execution failed",
    ):
        service.execute(
            proposal()
        )
