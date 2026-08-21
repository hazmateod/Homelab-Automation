"""
Remediation Autonomous Eligibility Policy.

Determines whether a deterministic remediation recommendation is eligible
for autonomous execution.

This service does not execute automation and does not bypass the existing
remediation execution policy, verification, approval, scheduling, or audit
services.

Production defaults to an empty autonomous allowlist. A remediation action
must be explicitly mapped and allowlisted before ALLOW_AUTOMATIC can ever
be returned.
"""

from himp.services.automation import (
    AutomationConfirmationRequiredError,
    AutomationDependencyNotFoundError,
    AutomationDependencyNotSatisfiedError,
    AutomationDisabledError,
)


class RemediationAutonomyPolicyService:
    """
    Fail-closed policy for low-risk autonomous remediation.
    """

    ALLOW_AUTOMATIC = "ALLOW_AUTOMATIC"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"

    def __init__(
        self,
        automation,
        allowlist=None,
    ):
        self.automation = automation

        # Production default: nothing is autonomous.
        #
        # Future entries must use this shape:
        #
        # {
        #     "update_host": {
        #         "conditions": {
        #             "SOME_SUPPORTED_CONDITION",
        #         },
        #         "target_types": {
        #             "host",
        #         },
        #         "risk_levels": {
        #             "maintenance",
        #         },
        #     },
        # }
        #
        self.allowlist = (
            allowlist
            if allowlist is not None
            else {}
        )

    @staticmethod
    def _decision(
        decision,
        *,
        reason,
        recommendation,
        task_id=None,
        target_type=None,
        target_id=None,
        risk_level=None,
    ):
        return {
            "decision": decision,
            "automatic_execution_permitted": (
                decision
                == RemediationAutonomyPolicyService.ALLOW_AUTOMATIC
            ),
            "recommendation_id": recommendation.get(
                "recommendation_id"
            ),
            "condition": recommendation.get(
                "condition"
            ),
            "task_id": task_id,
            "target_type": target_type,
            "target_id": target_id,
            "risk_level": risk_level,
            "reason": reason,
        }

    def evaluate(
        self,
        recommendation,
    ):
        if not isinstance(
            recommendation,
            dict,
        ):
            raise ValueError(
                "recommendation must be a dictionary"
            )

        condition = recommendation.get(
            "condition"
        )

        target = recommendation.get(
            "target"
        ) or {}

        target_type = target.get(
            "entity_type"
        )

        target_id = target.get(
            "entity_id"
        )

        automation_mapping = (
            recommendation.get(
                "automation"
            )
        )

        # Current Phase 13.1 recommendations intentionally
        # contain automation=None. Those remain operator
        # controlled and must not become automatic simply
        # because an executable task exists elsewhere.
        if not automation_mapping:
            return self._decision(
                self.REQUIRE_APPROVAL,
                reason=(
                    "Recommendation has no explicit "
                    "automation mapping."
                ),
                recommendation=recommendation,
                target_type=target_type,
                target_id=target_id,
            )

        if not isinstance(
            automation_mapping,
            dict,
        ):
            return self._decision(
                self.DENY,
                reason=(
                    "Recommendation automation mapping "
                    "is invalid."
                ),
                recommendation=recommendation,
                target_type=target_type,
                target_id=target_id,
            )

        task_id = automation_mapping.get(
            "task_id"
        )

        if not task_id:
            return self._decision(
                self.DENY,
                reason=(
                    "Recommendation automation mapping "
                    "does not identify a task."
                ),
                recommendation=recommendation,
                target_type=target_type,
                target_id=target_id,
            )

        if (
            not target_type
            or not target_id
        ):
            return self._decision(
                self.REQUIRE_APPROVAL,
                reason=(
                    "Recommendation target is not "
                    "bounded to an exact asset."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
            )

        mapping_target_type = (
            automation_mapping.get(
                "target_type"
            )
        )

        mapping_target_id = (
            automation_mapping.get(
                "target_id"
            )
        )

        if (
            mapping_target_type != target_type
            or mapping_target_id != target_id
        ):
            return self._decision(
                self.DENY,
                reason=(
                    "Automation mapping target does not "
                    "match the recommendation target."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
            )

        try:
            task = self.automation.find_task(
                task_id
            )

        except ValueError as error:
            return self._decision(
                self.DENY,
                reason=str(error),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
            )

        risk_level = task.get(
            "risk_level"
        )

        # Destructive work can never be autonomous through
        # this policy, even if someone accidentally adds it
        # to an allowlist.
        if risk_level == "destructive":
            return self._decision(
                self.DENY,
                reason=(
                    "Destructive automation cannot run "
                    "autonomously."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        rules = self.allowlist.get(
            task_id
        )

        if rules is None:
            return self._decision(
                self.REQUIRE_APPROVAL,
                reason=(
                    "Automation task is not explicitly "
                    "allowlisted for autonomous remediation."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        if condition not in rules.get(
            "conditions",
            set(),
        ):
            return self._decision(
                self.REQUIRE_APPROVAL,
                reason=(
                    "Recommendation condition is not "
                    "allowlisted for this autonomous task."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        if target_type not in rules.get(
            "target_types",
            set(),
        ):
            return self._decision(
                self.REQUIRE_APPROVAL,
                reason=(
                    "Recommendation target type is not "
                    "allowlisted for this autonomous task."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        if risk_level not in rules.get(
            "risk_levels",
            set(),
        ):
            return self._decision(
                self.REQUIRE_APPROVAL,
                reason=(
                    "Automation risk level is not "
                    "allowlisted for autonomous remediation."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        try:
            policy = (
                self.automation.validate_execution_policy(
                    task_id,
                    confirmed=False,
                )
            )

        except AutomationDisabledError as error:
            return self._decision(
                self.DENY,
                reason=str(error),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        except AutomationConfirmationRequiredError:
            return self._decision(
                self.DENY,
                reason=(
                    "Automation requires explicit "
                    "confirmation and cannot run "
                    "autonomously."
                ),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        except (
            AutomationDependencyNotFoundError,
            AutomationDependencyNotSatisfiedError,
        ) as error:
            return self._decision(
                self.DENY,
                reason=str(error),
                recommendation=recommendation,
                task_id=task_id,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
            )

        return self._decision(
            self.ALLOW_AUTOMATIC,
            reason=(
                "Recommendation passed the explicit "
                "autonomous remediation safety policy."
            ),
            recommendation=recommendation,
            task_id=task_id,
            target_type=target_type,
            target_id=target_id,
            risk_level=policy[
                "risk_level"
            ],
        )
