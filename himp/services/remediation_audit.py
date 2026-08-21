"""
Remediation Audit Service.

Persists the decision and execution outcome of a remediation action.
Actual automation execution history remains owned by the existing
AutomationExecutionRepository.
"""


class RemediationAuditService:
    """
    Records deterministic remediation audit events.
    """

    DECISIONS = {
        "ALLOW",
        "DENY",
        "CONFIRM_REQUIRED",
    }

    def __init__(
        self,
        repository,
    ):
        self.repository = repository

    def record(
        self,
        source_type,
        source_id,
        proposal,
        remediation,
        confirmed=False,
    ):
        if not isinstance(
            source_type,
            str,
        ) or not source_type.strip():
            raise ValueError(
                "source_type is required"
            )

        if not isinstance(
            source_id,
            str,
        ) or not source_id.strip():
            raise ValueError(
                "source_id is required"
            )

        task_id = proposal.get(
            "task_id"
        )

        if not isinstance(
            task_id,
            str,
        ) or not task_id.strip():
            raise ValueError(
                "task_id is required"
            )

        decision = remediation.get(
            "decision"
        )

        if decision not in self.DECISIONS:
            raise ValueError(
                f"Invalid remediation decision: {decision}"
            )

        policy = remediation.get(
            "policy",
            {}
        )

        evidence = proposal.get(
            "evidence",
            policy.get(
                "evidence",
                {},
            ),
        )

        reason = proposal.get(
            "reason",
            policy.get(
                "reason",
                "",
            ),
        )

        risk_level = policy.get(
            "risk_level"
        )

        confirmation_required = bool(
            policy.get(
                "confirmation_required",
                False,
            )
        )

        execution = remediation.get(
            "execution"
        )

        execution_id = None
        execution_success = None

        if execution is not None:
            execution_id = execution.get(
                "id"
            )
            execution_success = execution.get(
                "success"
            )

        verification = remediation.get(
            "verification"
        )

        verification_status = None
        verification_success = None
        verification_evidence = None

        if verification is not None:
            verification_status = (
                verification.get(
                    "status"
                )
            )

            verification_success = (
                verification.get(
                    "success"
                )
            )

            verification_evidence = (
                verification
            )

        return self.repository.save(
            source_type=source_type,
            source_id=source_id,
            task_id=task_id,
            decision=decision,
            reason=reason,
            evidence=evidence,
            risk_level=risk_level,
            confirmation_required=confirmation_required,
            confirmed=bool(confirmed),
            execution_id=execution_id,
            execution_success=execution_success,
            verification_status=verification_status,
            verification_success=verification_success,
            verification_evidence=verification_evidence,
        )
