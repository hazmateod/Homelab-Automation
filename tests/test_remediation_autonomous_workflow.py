from himp.services.remediation_autonomous_workflow import (
    RemediationAutonomousWorkflowService,
)


class FakeRecommendations:
    def __init__(
        self,
        recommendations,
    ):
        self.recommendations = (
            recommendations
        )
        self.calls = []

    def recommend(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        self.calls.append(
            {
                "entity_type":
                    entity_type,
                "entity_id":
                    entity_id,
                "limit":
                    limit,
            }
        )

        return {
            "entity_type":
                entity_type,
            "entity_id":
                entity_id,
            "recommendation_count":
                len(
                    self.recommendations
                ),
            "execution_performed":
                False,
            "recommendations":
                self.recommendations,
        }


class FakeExecution:
    def __init__(
        self,
        results,
    ):
        self.results = list(
            results
        )
        self.calls = []

    def execute(
        self,
        recommendation,
        *,
        source_type,
        source_id,
    ):
        self.calls.append(
            {
                "recommendation":
                    recommendation,
                "source_type":
                    source_type,
                "source_id":
                    source_id,
            }
        )

        return self.results.pop(0)


def recommendation(
    recommendation_id,
    decision,
):
    return {
        "recommendation_id":
            recommendation_id,
        "condition":
            recommendation_id.split(
                ":",
                1,
            )[0],
        "target": {
            "entity_type": "host",
            "entity_id":
                recommendation_id.split(
                    ":",
                    1,
                )[1],
        },
        "autonomy": {
            "decision":
                decision,
            "automatic_execution_permitted":
                decision
                == "ALLOW_AUTOMATIC",
        },
    }


def test_empty_recommendations_perform_no_execution():
    recommendations = (
        FakeRecommendations([])
    )

    execution = FakeExecution([])

    service = (
        RemediationAutonomousWorkflowService(
            recommendations=
                recommendations,
            execution=execution,
        )
    )

    result = service.run(
        source_type="application",
        source_id="himp",
    )

    assert result[
        "recommendation_count"
    ] == 0

    assert result[
        "executed_count"
    ] == 0

    assert result[
        "execution_performed"
    ] is False

    assert execution.calls == []


def test_require_approval_is_counted_without_execution():
    item = recommendation(
        "HOST_UNHEALTHY:pve01",
        "REQUIRE_APPROVAL",
    )

    recommendations = (
        FakeRecommendations(
            [item]
        )
    )

    execution = FakeExecution(
        [
            {
                "decision":
                    "REQUIRE_APPROVAL",
                "automatic_execution_permitted":
                    False,
                "executed":
                    False,
                "autonomy":
                    item["autonomy"],
            }
        ]
    )

    service = (
        RemediationAutonomousWorkflowService(
            recommendations=
                recommendations,
            execution=execution,
        )
    )

    result = service.run(
        source_type="application",
        source_id="himp",
    )

    assert result[
        "approval_required_count"
    ] == 1

    assert result[
        "automatic_eligible_count"
    ] == 0

    assert result[
        "executed_count"
    ] == 0

    assert result[
        "execution_performed"
    ] is False


def test_mixed_autonomous_results_are_summarized():
    automatic_one = recommendation(
        "PACKAGE_UPDATES_AVAILABLE:pve01",
        "ALLOW_AUTOMATIC",
    )

    automatic_two = recommendation(
        "PACKAGE_UPDATES_AVAILABLE:pve02",
        "ALLOW_AUTOMATIC",
    )

    denied = recommendation(
        "UNSUPPORTED:pve03",
        "DENY",
    )

    recommendations = (
        FakeRecommendations(
            [
                automatic_one,
                automatic_two,
                denied,
            ]
        )
    )

    execution = FakeExecution(
        [
            {
                "decision":
                    "COMPLETED",
                "executed":
                    True,
                "audit_id":
                    41,
            },
            {
                "decision":
                    "FAILED",
                "executed":
                    True,
                "audit_id":
                    42,
            },
            {
                "decision":
                    "DENY",
                "executed":
                    False,
            },
        ]
    )

    service = (
        RemediationAutonomousWorkflowService(
            recommendations=
                recommendations,
            execution=execution,
        )
    )

    result = service.run(
        source_type="application",
        source_id="himp",
        baseline="baseline-a",
        change_limit=7,
    )

    assert result[
        "recommendation_count"
    ] == 3

    assert result[
        "automatic_eligible_count"
    ] == 2

    assert result[
        "executed_count"
    ] == 2

    assert result[
        "completed_count"
    ] == 1

    assert result[
        "failed_count"
    ] == 1

    assert result[
        "denied_count"
    ] == 1

    assert result[
        "approval_required_count"
    ] == 0

    assert result[
        "execution_performed"
    ] is True

    assert result[
        "audit_ids"
    ] == [
        41,
        42,
    ]

    assert result[
        "baseline"
    ] == "baseline-a"

    assert result[
        "change_limit"
    ] == 7


def test_every_recommendation_is_rechecked_by_execution_coordinator():
    items = [
        recommendation(
            "HOST_UNHEALTHY:pve01",
            "REQUIRE_APPROVAL",
        ),
        recommendation(
            "HOST_FLAPPING:pve02",
            "REQUIRE_APPROVAL",
        ),
    ]

    execution = FakeExecution(
        [
            {
                "decision":
                    "REQUIRE_APPROVAL",
                "executed":
                    False,
            },
            {
                "decision":
                    "REQUIRE_APPROVAL",
                "executed":
                    False,
            },
        ]
    )

    service = (
        RemediationAutonomousWorkflowService(
            recommendations=
                FakeRecommendations(
                    items
                ),
            execution=execution,
        )
    )

    service.run(
        source_type="application",
        source_id="himp",
    )

    assert len(
        execution.calls
    ) == 2
