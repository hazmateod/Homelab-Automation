"""
Remediation Workflow Service.

Coordinates remediation proposal generation with the existing
remediation policy and execution services.
"""

from himp.database.remediation_audit import (
    RemediationAuditRepository,
)
from himp.services.automation import AutomationService
from himp.services.remediation_audit import (
    RemediationAuditService,
)
from himp.services.remediation_execution import (
    RemediationExecutionService,
)
from himp.services.remediation_policy import (
    RemediationPolicyService,
)
from himp.services.remediation_proposals import (
    RemediationProposalService,
)
from himp.services.remediation_verification import (
    RemediationVerificationService,
)


class RemediationWorkflowService:
    """
    Coordinates remediation proposals and their execution.

    Proposal generation, policy evaluation, and automation execution
    remain delegated to their existing services.
    """

    def __init__(
        self,
        proposals=None,
        execution=None,
        audit=None,
        verification=None,
    ):
        self.proposals = (
            proposals
            or RemediationProposalService()
        )

        if execution is not None:
            self.execution = execution
        else:
            automation = AutomationService()
            policy = RemediationPolicyService(
                automation=automation,
            )

            self.execution = RemediationExecutionService(
                policy=policy,
                automation=automation,
            )

        self.audit = (
            audit
            if audit is not None
            else RemediationAuditService(
                repository=RemediationAuditRepository()
            )
        )

        self.verification = (
            verification
            if verification is not None
            else RemediationVerificationService()
        )

    def run(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
        confirmed=False,
    ):
        result = self.proposals.propose(
            source_type=source_type,
            source_id=source_id,
            baseline=baseline,
            change_limit=change_limit,
        )

        proposals = result["proposals"]
        results = []
        audit_ids = []
        verification_count = 0
        verified_count = 0
        unverified_count = 0

        for proposal in proposals:
            remediation = self.execution.execute(
                proposal,
                confirmed=confirmed,
            )

            if remediation["decision"] == "ALLOW":
                verification_result = self.verification.verify(
                    proposal=proposal,
                    remediation=remediation,
                )

                remediation["verification"] = (
                    verification_result
                )

                verification_count += 1

                if verification_result.get(
                    "success"
                ):
                    verified_count += 1
                else:
                    unverified_count += 1

            audit_record = self.audit.record(
                source_type=source_type,
                source_id=source_id,
                proposal=proposal,
                remediation=remediation,
                confirmed=confirmed,
            )

            if audit_record is not None:
                audit_id = audit_record.get("id")

                if audit_id is not None:
                    audit_ids.append(audit_id)

            results.append(
                remediation
            )

        executed_count = sum(
            1
            for item in results
            if item["decision"] == "ALLOW"
        )

        blocked_count = sum(
            1
            for item in results
            if item["decision"] != "ALLOW"
        )

        return {
            "source_type": source_type,
            "source_id": source_id,
            "baseline": baseline,
            "proposal_count": len(proposals),
            "executed_count": executed_count,
            "blocked_count": blocked_count,
            "verification_count": verification_count,
            "verified_count": verified_count,
            "unverified_count": unverified_count,
            "audit_ids": audit_ids,
            "results": results,
        }
