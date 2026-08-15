"""
Remediation Workflow Service.

Coordinates remediation proposal generation with the existing
remediation policy and execution services.
"""

from himp.services.automation import AutomationService
from himp.services.remediation_execution import (
    RemediationExecutionService,
)
from himp.services.remediation_policy import (
    RemediationPolicyService,
)
from himp.services.remediation_proposals import (
    RemediationProposalService,
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

        for proposal in proposals:
            results.append(
                self.execution.execute(
                    proposal,
                    confirmed=confirmed,
                )
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
            "results": results,
        }
