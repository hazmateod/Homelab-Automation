import pytest

from himp.services.remediation_approvals import (
    RemediationApprovalService,
)
from himp.services.remediation_recommendations import (
    RemediationRecommendationService,
)


class FakeHealth:
    def correlate(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        return {
            "hosts": [
                {
                    "hostname": "pve01",
                    "depth": 1,
                    "path": [],
                    "analysis": {
                        "history_available": True,
                        "current_state": "UNHEALTHY",
                        "current_status": "FAIL",
                        "observation_count": 3,
                        "current_streak": 2,
                        "failure_percentage": 66.67,
                        "unhealthy_percentage": 66.67,
                        "transition_count": 1,
                        "flap_count": 0,
                        "is_flapping": False,
                        "latest_observation": {
                            "status": "FAIL",
                        },
                    },
                }
            ]
        }


class FakeImpact:
    def impact(
        self,
        entity_type,
        entity_id,
    ):
        return {
            "assets": [],
        }


class FakeAutonomy:
    def __init__(
        self,
        decision="REQUIRE_APPROVAL",
    ):
        self.decision = decision
        self.calls = []

    def evaluate(
        self,
        recommendation,
    ):
        self.calls.append(
            recommendation[
                "recommendation_id"
            ]
        )

        return {
            "decision": self.decision,
            "automatic_execution_permitted": (
                self.decision
                == "ALLOW_AUTOMATIC"
            ),
            "reason": "test",
        }


class FakeRepository:
    def __init__(self):
        self.created = []

    def create(
        self,
        recommendation,
        source_type,
        source_id,
        requested_by,
        task_id,
    ):
        record = {
            "id": 7,
            "recommendation_id":
                recommendation[
                    "recommendation_id"
                ],
            "status": "PENDING",
        }

        self.created.append(record)

        return record


class FakeRecommendations:
    def __init__(
        self,
        recommendation,
    ):
        self.recommendation = (
            recommendation
        )

    def recommend(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        return {
            "recommendations": [
                self.recommendation
            ]
        }


def recommendation(
    decision,
):
    return {
        "recommendation_id":
            "HOST_UNHEALTHY:pve01",
        "condition":
            "HOST_UNHEALTHY",
        "severity":
            "CRITICAL",
        "target": {
            "entity_type": "host",
            "entity_id": "pve01",
        },
        "evidence": {},
        "rationale": "Host unhealthy.",
        "recommended_action":
            "Investigate.",
        "automation": None,
        "autonomy": {
            "decision": decision,
            "automatic_execution_permitted":
                decision
                == "ALLOW_AUTOMATIC",
        },
    }


def test_recommendations_include_autonomy_decision():
    autonomy = FakeAutonomy()

    service = (
        RemediationRecommendationService(
            health=FakeHealth(),
            impact=FakeImpact(),
            autonomy=autonomy,
        )
    )

    result = service.recommend(
        entity_type="application",
        entity_id="himp",
    )

    assert (
        result["recommendations"][0][
            "autonomy"
        ]["decision"]
        == "REQUIRE_APPROVAL"
    )

    assert autonomy.calls == [
        "HOST_UNHEALTHY:pve01"
    ]


def test_require_approval_can_enter_queue():
    repository = FakeRepository()

    service = RemediationApprovalService(
        repository=repository,
        recommendations=FakeRecommendations(
            recommendation(
                "REQUIRE_APPROVAL"
            )
        ),
    )

    result = service.enqueue(
        entity_type="application",
        entity_id="himp",
        recommendation_id=(
            "HOST_UNHEALTHY:pve01"
        ),
        requested_by="admin",
    )

    assert result["status"] == (
        "PENDING"
    )

    assert len(
        repository.created
    ) == 1


def test_denied_recommendation_cannot_enter_queue():
    repository = FakeRepository()

    service = RemediationApprovalService(
        repository=repository,
        recommendations=FakeRecommendations(
            recommendation(
                "DENY"
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="denied by autonomous",
    ):
        service.enqueue(
            entity_type="application",
            entity_id="himp",
            recommendation_id=(
                "HOST_UNHEALTHY:pve01"
            ),
            requested_by="admin",
        )

    assert repository.created == []


def test_automatic_recommendation_skips_approval_queue():
    repository = FakeRepository()

    service = RemediationApprovalService(
        repository=repository,
        recommendations=FakeRecommendations(
            recommendation(
                "ALLOW_AUTOMATIC"
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="eligible for automatic",
    ):
        service.enqueue(
            entity_type="application",
            entity_id="himp",
            recommendation_id=(
                "HOST_UNHEALTHY:pve01"
            ),
            requested_by="admin",
        )

    assert repository.created == []
