from himp.services.automation import (
    AutomationConfirmationRequiredError,
    AutomationDependencyNotSatisfiedError,
    AutomationDisabledError,
)
from himp.services.remediation_autonomy import (
    RemediationAutonomyPolicyService,
)


class FakeAutomation:
    def __init__(
        self,
        *,
        enabled=True,
        risk_level="maintenance",
        confirmation_required=False,
        dependency_failure=False,
    ):
        self.task = {
            "id": "update_host",
            "enabled": enabled,
            "risk_level": risk_level,
        }

        self.confirmation_required = (
            confirmation_required
        )

        self.dependency_failure = (
            dependency_failure
        )

        self.policy_calls = []

    def find_task(
        self,
        task_id,
    ):
        if task_id != "update_host":
            raise ValueError(
                "Automation task does not exist: "
                f"{task_id}"
            )

        return self.task

    def validate_execution_policy(
        self,
        task_id,
        confirmed=False,
    ):
        self.policy_calls.append(
            {
                "task_id": task_id,
                "confirmed": confirmed,
            }
        )

        if not self.task["enabled"]:
            raise AutomationDisabledError(
                "Automation task is disabled: "
                f"{task_id}"
            )

        if self.confirmation_required:
            raise AutomationConfirmationRequiredError(
                "confirmation required"
            )

        if self.dependency_failure:
            raise AutomationDependencyNotSatisfiedError(
                "dependency failed"
            )

        return {
            "task_id": task_id,
            "enabled": True,
            "risk_level":
                self.task["risk_level"],
            "confirmed": confirmed,
        }


def recommendation(
    *,
    condition="PACKAGE_UPDATES_AVAILABLE",
    automation=True,
    target_type="host",
    target_id="pve01",
    task_id="update_host",
    mapping_target_type=None,
    mapping_target_id=None,
):
    result = {
        "recommendation_id":
            f"{condition}:{target_id}",
        "condition": condition,
        "target": {
            "entity_type": target_type,
            "entity_id": target_id,
        },
    }

    if automation is True:
        result["automation"] = {
            "task_id": task_id,
            "target_type": (
                mapping_target_type
                if mapping_target_type
                is not None
                else target_type
            ),
            "target_id": (
                mapping_target_id
                if mapping_target_id
                is not None
                else target_id
            ),
        }

    elif automation is False:
        result["automation"] = None

    else:
        result["automation"] = (
            automation
        )

    return result


def allowlist():
    return {
        "update_host": {
            "conditions": {
                "PACKAGE_UPDATES_AVAILABLE",
            },
            "target_types": {
                "host",
            },
            "risk_levels": {
                "maintenance",
            },
        }
    }


def make_service(
    automation=None,
    rules=None,
):
    return (
        RemediationAutonomyPolicyService(
            automation=(
                automation
                or FakeAutomation()
            ),
            allowlist=(
                rules
                if rules is not None
                else {}
            ),
        )
    )


def test_current_recommendation_without_automation_requires_approval():
    service = make_service()

    result = service.evaluate(
        recommendation(
            condition="HOST_UNHEALTHY",
            automation=False,
        )
    )

    assert result["decision"] == (
        "REQUIRE_APPROVAL"
    )

    assert (
        result[
            "automatic_execution_permitted"
        ]
        is False
    )


def test_task_must_be_explicitly_allowlisted():
    service = make_service()

    result = service.evaluate(
        recommendation()
    )

    assert result["decision"] == (
        "REQUIRE_APPROVAL"
    )


def test_exact_target_is_required():
    service = make_service(
        rules=allowlist()
    )

    result = service.evaluate(
        recommendation(
            target_id="",
        )
    )

    assert result["decision"] == (
        "REQUIRE_APPROVAL"
    )


def test_mapping_target_must_match_recommendation_target():
    service = make_service(
        rules=allowlist()
    )

    result = service.evaluate(
        recommendation(
            mapping_target_id="pve02",
        )
    )

    assert result["decision"] == "DENY"


def test_condition_must_be_allowlisted():
    service = make_service(
        rules=allowlist()
    )

    result = service.evaluate(
        recommendation(
            condition="HOST_UNHEALTHY"
        )
    )

    assert result["decision"] == (
        "REQUIRE_APPROVAL"
    )


def test_risk_level_must_be_allowlisted():
    service = make_service(
        automation=FakeAutomation(
            risk_level="read_only"
        ),
        rules=allowlist(),
    )

    result = service.evaluate(
        recommendation()
    )

    assert result["decision"] == (
        "REQUIRE_APPROVAL"
    )


def test_destructive_automation_is_always_denied():
    rules = allowlist()

    rules["update_host"][
        "risk_levels"
    ].add(
        "destructive"
    )

    service = make_service(
        automation=FakeAutomation(
            risk_level="destructive"
        ),
        rules=rules,
    )

    result = service.evaluate(
        recommendation()
    )

    assert result["decision"] == "DENY"


def test_disabled_automation_is_denied():
    service = make_service(
        automation=FakeAutomation(
            enabled=False
        ),
        rules=allowlist(),
    )

    result = service.evaluate(
        recommendation()
    )

    assert result["decision"] == "DENY"


def test_confirmation_required_is_denied():
    service = make_service(
        automation=FakeAutomation(
            confirmation_required=True
        ),
        rules=allowlist(),
    )

    result = service.evaluate(
        recommendation()
    )

    assert result["decision"] == "DENY"


def test_dependency_failure_is_denied():
    service = make_service(
        automation=FakeAutomation(
            dependency_failure=True
        ),
        rules=allowlist(),
    )

    result = service.evaluate(
        recommendation()
    )

    assert result["decision"] == "DENY"


def test_explicit_bounded_allowlisted_action_is_automatic():
    automation = FakeAutomation()

    service = make_service(
        automation=automation,
        rules=allowlist(),
    )

    result = service.evaluate(
        recommendation()
    )

    assert result["decision"] == (
        "ALLOW_AUTOMATIC"
    )

    assert (
        result[
            "automatic_execution_permitted"
        ]
        is True
    )

    assert result["task_id"] == (
        "update_host"
    )

    assert result["target_type"] == (
        "host"
    )

    assert result["target_id"] == (
        "pve01"
    )

    assert automation.policy_calls == [
        {
            "task_id": "update_host",
            "confirmed": False,
        }
    ]
