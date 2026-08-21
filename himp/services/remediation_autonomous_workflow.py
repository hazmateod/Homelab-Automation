"""
Autonomous Remediation Workflow.

Evaluates deterministic remediation recommendations through the autonomous
eligibility policy and sends only ALLOW_AUTOMATIC recommendations to the
autonomous execution coordinator.

REQUIRE_APPROVAL recommendations remain operator-controlled.
DENY recommendations never execute.

This workflow does not automatically create approval records. That avoids
duplicate approval queue entries during recurring operational evaluation.
"""

class RemediationAutonomousWorkflowService:
    """
    Coordinate recommendation-level autonomous remediation.
    """

    def __init__(
        self,
        recommendations,
        execution,
    ):
        self.recommendations = (
            recommendations
        )

        self.execution = execution

    def run(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
        limit=100,
    ):
        recommendation_result = (
            self.recommendations.recommend(
                entity_type=source_type,
                entity_id=source_id,
                limit=limit,
            )
        )

        recommendations = (
            recommendation_result[
                "recommendations"
            ]
        )

        results = []
        audit_ids = []

        automatic_eligible_count = 0
        executed_count = 0
        completed_count = 0
        failed_count = 0
        approval_required_count = 0
        denied_count = 0

        for recommendation in recommendations:
            autonomy = (
                recommendation.get(
                    "autonomy"
                )
                or {}
            )

            decision = autonomy.get(
                "decision"
            )

            if decision == "ALLOW_AUTOMATIC":
                automatic_eligible_count += 1

            result = self.execution.execute(
                recommendation,
                source_type=source_type,
                source_id=source_id,
            )

            result_decision = (
                result.get(
                    "decision"
                )
            )

            if result.get(
                "executed"
            ):
                executed_count += 1

            if result_decision == "COMPLETED":
                completed_count += 1

            elif result_decision == "FAILED":
                failed_count += 1

            elif result_decision == "REQUIRE_APPROVAL":
                approval_required_count += 1

            elif result_decision == "DENY":
                denied_count += 1

            audit_id = result.get(
                "audit_id"
            )

            if audit_id is not None:
                audit_ids.append(
                    audit_id
                )

            results.append(
                {
                    "recommendation_id":
                        recommendation.get(
                            "recommendation_id"
                        ),
                    "condition":
                        recommendation.get(
                            "condition"
                        ),
                    "target":
                        recommendation.get(
                            "target"
                        ),
                    "result":
                        result,
                }
            )

        return {
            "source_type": source_type,
            "source_id": source_id,
            "baseline": baseline,
            "change_limit": change_limit,
            "recommendation_count":
                len(recommendations),
            "automatic_eligible_count":
                automatic_eligible_count,
            "executed_count":
                executed_count,
            "completed_count":
                completed_count,
            "failed_count":
                failed_count,
            "approval_required_count":
                approval_required_count,
            "denied_count":
                denied_count,
            "execution_performed":
                executed_count > 0,
            "audit_ids": audit_ids,
            "results": results,
        }
