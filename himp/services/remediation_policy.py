"""
Remediation Policy Service.

Evaluates proposed remediation actions against the existing
automation execution policy without executing the automation.
"""


class RemediationPolicyService:
    """
    Determines whether a proposed remediation may proceed.
    """

    def __init__(
        self,
        automation,
    ):
        self.automation = automation

    def evaluate(
        self,
        proposal,
        confirmed=False,
    ):
        task_id = proposal["task_id"]

        task = self.automation.find_task(
            task_id
        )

        try:
            policy = self.automation.validate_execution_policy(
                task_id,
                confirmed=confirmed,
            )

        except RuntimeError as error:

            message = str(error)

            if message == "automation disabled":
                return {
                    "decision": "DENY",
                    "task_id": task_id,
                    "reason": message,
                    "evidence": proposal["evidence"],
                    "risk_level": task["risk_level"],
                    "confirmation_required": False,
                }

            if message == "confirmation required":
                return {
                    "decision": "CONFIRM_REQUIRED",
                    "task_id": task_id,
                    "reason": proposal["reason"],
                    "evidence": proposal["evidence"],
                    "risk_level": task["risk_level"],
                    "confirmation_required": True,
                }

            raise

        return {
            "decision": "ALLOW",
            "task_id": task_id,
            "reason": proposal["reason"],
            "evidence": proposal["evidence"],
            "risk_level": policy["risk_level"],
            "confirmation_required": False,
        }
