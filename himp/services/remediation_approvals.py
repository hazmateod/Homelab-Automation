"""
Remediation Approval Queue Service.

Coordinates durable operator approval decisions without scheduling or
executing remediation.
"""

from himp.database.remediation_approvals import (
    RemediationApprovalRepository,
)
from himp.services.remediation_recommendations import (
    RemediationRecommendationService,
)


class RemediationApprovalService:
    """
    Manage approval queue lifecycle independently from execution.
    """

    def __init__(
        self,
        repository=None,
        recommendations=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else RemediationApprovalRepository()
        )

        self.recommendations = (
            recommendations
            if recommendations is not None
            else RemediationRecommendationService()
        )

    def enqueue(
        self,
        entity_type,
        entity_id,
        recommendation_id,
        requested_by,
        limit=100,
    ):
        result = self.recommendations.recommend(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

        recommendation = next(
            (
                item
                for item in result[
                    "recommendations"
                ]
                if item[
                    "recommendation_id"
                ] == recommendation_id
            ),
            None,
        )

        if recommendation is None:
            raise ValueError(
                "recommendation is not currently supported "
                "by deterministic evidence"
            )

        return self.repository.create(
            recommendation=recommendation,
            source_type=entity_type,
            source_id=entity_id,
            requested_by=requested_by,
        )

    def list(
        self,
        limit=100,
        status=None,
    ):
        approvals = self.repository.list(
            limit=limit,
            status=status,
        )

        return {
            "count": len(approvals),
            "summary": (
                self.repository.summary()
            ),
            "approvals": approvals,
        }

    def get(
        self,
        approval_id,
    ):
        approval = self.repository.find(
            approval_id
        )

        if approval is None:
            raise KeyError(
                f"approval does not exist: {approval_id}"
            )

        return approval

    def approve(
        self,
        approval_id,
        decided_by,
        decision_note=None,
    ):
        return self.repository.decide(
            approval_id=approval_id,
            status="APPROVED",
            decided_by=decided_by,
            decision_note=decision_note,
        )

    def deny(
        self,
        approval_id,
        decided_by,
        decision_note=None,
    ):
        return self.repository.decide(
            approval_id=approval_id,
            status="DENIED",
            decided_by=decided_by,
            decision_note=decision_note,
        )
