"""
Remediation Proposal Service.

Converts infrastructure intelligence findings into explicit remediation
proposals without evaluating or executing automation policy.
"""

from himp.services.infrastructure_intelligence import (
    InfrastructureIntelligenceService,
)


class RemediationProposalService:
    """
    Generates deterministic remediation proposals.
    """

    TASK_ID = "scheduled_updates"

    def __init__(
        self,
        intelligence=None,
    ):
        self.intelligence = (
            intelligence
            or InfrastructureIntelligenceService()
        )

    def propose(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
    ):
        intelligence = self.intelligence.inspect(
            source_type=source_type,
            source_id=source_id,
            baseline=baseline,
            change_limit=change_limit,
        )

        proposals = []

        for relationship in intelligence["relationships"]:
            health_status = relationship["health_status"]

            if health_status not in {
                "FAIL",
                "WARNING",
            }:
                continue

            health_description = (
                "failed"
                if health_status == "FAIL"
                else "warning"
            )

            proposals.append(
                {
                    "task_id": self.TASK_ID,
                    "reason": (
                        f"Related host "
                        f"{relationship['target_id']} "
                        f"has {health_description} health."
                    ),
                    "evidence": {
                        "source_type": source_type,
                        "source_id": source_id,
                        "target_type": relationship[
                            "target_type"
                        ],
                        "target_id": relationship[
                            "target_id"
                        ],
                        "health_status": health_status,
                    },
                }
            )

        if intelligence["drift"]:
            affected_host = intelligence["drift"][0][
                "hostname"
            ]

            proposals.append(
                {
                    "task_id": self.TASK_ID,
                    "reason": (
                        "Inventory baseline drift detected "
                        f"for {affected_host}."
                    ),
                    "evidence": {
                        "baseline": baseline,
                        "drift": intelligence["drift"],
                    },
                }
            )

        return {
            "source_type": source_type,
            "source_id": source_id,
            "proposals": proposals,
        }
