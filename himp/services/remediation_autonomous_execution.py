"""
Autonomous Remediation Execution Coordinator.

Coordinates explicitly eligible autonomous remediation through the existing
remediation execution, verification, and audit services.

This service never converts REQUIRE_APPROVAL or DENY into execution.
Production remains unable to reach ALLOW_AUTOMATIC while the autonomous
allowlist is empty.
"""

from himp.database.remediation_audit import (
    RemediationAuditRepository,
)
from himp.services.remediation_audit import (
    RemediationAuditService,
)
from himp.services.remediation_autonomy import (
    RemediationAutonomyPolicyService,
)
from himp.services.remediation_verification import (
    RemediationVerificationService,
)


class RemediationAutonomousExecutionService:
    """
    Execute only explicitly ALLOW_AUTOMATIC recommendations.
    """

    def __init__(
        self,
        autonomy,
        execution,
        verification=None,
        audit=None,
    ):
        self.autonomy = autonomy
        self.execution = execution

        self.verification = (
            verification
            if verification is not None
            else RemediationVerificationService()
        )

        self.audit = (
            audit
            if audit is not None
            else RemediationAuditService(
                repository=(
                    RemediationAuditRepository()
                )
            )
        )

    @staticmethod
    def _proposal(
        recommendation,
        decision,
    ):
        automation = (
            recommendation.get(
                "automation"
            )
            or {}
        )

        target = (
            recommendation.get(
                "target"
            )
            or {}
        )

        evidence = dict(
            recommendation.get(
                "evidence"
            )
            or {}
        )

        evidence.update(
            {
                "condition":
                    recommendation.get(
                        "condition"
                    ),
                "target_type":
                    target.get(
                        "entity_type"
                    ),
                "target_id":
                    target.get(
                        "entity_id"
                    ),
                "recommendation_id":
                    recommendation.get(
                        "recommendation_id"
                    ),
                "autonomous": True,
                "autonomy_decision":
                    decision,
            }
        )

        return {
            "task_id":
                automation["task_id"],
            "condition":
                recommendation.get(
                    "condition"
                ),
            "reason":
                recommendation.get(
                    "rationale"
                )
                or recommendation.get(
                    "recommended_action"
                )
                or (
                    "Autonomous remediation "
                    "recommendation."
                ),
            "evidence": evidence,
        }

    def execute(
        self,
        recommendation,
        *,
        source_type,
        source_id,
    ):
        autonomy = self.autonomy.evaluate(
            recommendation
        )

        if autonomy["decision"] != (
            RemediationAutonomyPolicyService.ALLOW_AUTOMATIC
        ):
            return {
                "decision":
                    autonomy["decision"],
                "automatic_execution_permitted":
                    False,
                "executed":
                    False,
                "autonomy":
                    autonomy,
            }

        target_id = autonomy.get(
            "target_id"
        )

        if not target_id:
            # Defense in depth. The policy should already
            # prevent this state.
            return {
                "decision": "DENY",
                "automatic_execution_permitted":
                    False,
                "executed": False,
                "autonomy": {
                    **autonomy,
                    "decision": "DENY",
                    "automatic_execution_permitted":
                        False,
                    "reason": (
                        "Autonomous execution requires "
                        "an exact target."
                    ),
                },
            }

        proposal = self._proposal(
            recommendation,
            autonomy,
        )

        remediation = (
            self.execution.execute(
                proposal,
                confirmed=False,
                limit=target_id,
            )
        )

        # Re-evaluation by the existing execution policy
        # remains mandatory. ALLOW_AUTOMATIC cannot override
        # a later execution-policy block.
        if remediation[
            "decision"
        ] != "ALLOW":
            audit_record = (
                self.audit.record(
                    source_type=source_type,
                    source_id=source_id,
                    proposal=proposal,
                    remediation=remediation,
                    confirmed=False,
                )
            )

            return {
                "decision":
                    remediation[
                        "decision"
                    ],
                "automatic_execution_permitted":
                    True,
                "executed":
                    False,
                "autonomy":
                    autonomy,
                "remediation":
                    remediation,
                "audit_id": (
                    audit_record.get(
                        "id"
                    )
                    if audit_record
                    is not None
                    else None
                ),
            }

        verification = (
            self.verification.verify(
                proposal=proposal,
                remediation=remediation,
            )
        )

        remediation[
            "verification"
        ] = verification

        audit_record = self.audit.record(
            source_type=source_type,
            source_id=source_id,
            proposal=proposal,
            remediation=remediation,
            confirmed=False,
        )

        execution = (
            remediation.get(
                "execution"
            )
            or {}
        )

        execution_success = (
            execution.get(
                "success"
            )
            is not False
        )

        verified = bool(
            verification.get(
                "success"
            )
        )

        return {
            "decision":
                "COMPLETED"
                if (
                    execution_success
                    and verified
                )
                else "FAILED",
            "automatic_execution_permitted":
                True,
            "executed": True,
            "autonomy": autonomy,
            "remediation": remediation,
            "verification": verification,
            "audit_id": (
                audit_record.get(
                    "id"
                )
                if audit_record
                is not None
                else None
            ),
        }
