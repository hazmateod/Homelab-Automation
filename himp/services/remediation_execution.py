"""
Remediation Execution Service.

Evaluates a remediation proposal against policy and executes the
existing automation only when policy explicitly allows it.
"""

from himp.services.remediation_policy import (
    RemediationPolicyService,
)


class RemediationExecutionService:
    """
    Coordinates remediation policy evaluation and execution.
    """

    def __init__(
        self,
        policy,
        automation,
    ):
        self.policy = policy
        self.automation = automation

    def execute(
        self,
        proposal,
        confirmed=False,
    ):
        policy = self.policy.evaluate(
            proposal,
            confirmed=confirmed,
        )

        result = {
            "decision": policy["decision"],
            "policy": policy,
        }

        if policy["decision"] != "ALLOW":
            result.update(
                {
                    key: value
                    for key, value in policy.items()
                    if key not in {
                        "decision",
                    }
                }
            )

            return result

        execution = self.automation.run(
            proposal["task_id"],
            confirmed=confirmed,
        )

        result["execution"] = execution

        return result
