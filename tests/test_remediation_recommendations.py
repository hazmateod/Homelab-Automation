from himp.services.remediation_recommendations import (
    RemediationRecommendationService,
)


def analysis(
    *,
    history_available=True,
    current_status="PASS",
    current_state="HEALTHY",
    observation_count=5,
    current_streak=5,
    failure_percentage=0.0,
    unhealthy_percentage=0.0,
    transition_count=0,
    flap_count=0,
    is_flapping=False,
):
    return {
        "history_available": history_available,
        "observation_count": observation_count,
        "pass_count": (
            observation_count
            if current_state == "HEALTHY"
            else 0
        ),
        "warning_count": 0,
        "fail_count": 0,
        "unknown_count": 0,
        "unhealthy_count": (
            0
            if current_state == "HEALTHY"
            else observation_count
        ),
        "unhealthy_percentage": unhealthy_percentage,
        "failure_percentage": failure_percentage,
        "transition_count": transition_count,
        "flap_count": flap_count,
        "is_flapping": is_flapping,
        "current_status": current_status,
        "current_state": current_state,
        "current_streak": current_streak,
        "first_observation": "2026-08-20T00:00:00",
        "latest_observation": "2026-08-20T01:00:00",
        "observed_unhealthy_duration_seconds": 0.0,
    }


class FakeHealth:
    def __init__(
        self,
        hosts=None,
        host_result=None,
    ):
        self.hosts = hosts or []
        self.host_result = host_result
        self.correlate_calls = []
        self.host_calls = []

    def correlate(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        self.correlate_calls.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "limit": limit,
            }
        )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "limit": limit,
            "host_count": len(self.hosts),
            "history_available_hosts": sum(
                item["history_available"]
                for item in self.hosts
            ),
            "history_unavailable_hosts": sum(
                not item["history_available"]
                for item in self.hosts
            ),
            "unhealthy_hosts": 0,
            "flapping_hosts": 0,
            "hosts": self.hosts,
        }

    def host(
        self,
        hostname,
        limit=100,
    ):
        self.host_calls.append(
            {
                "hostname": hostname,
                "limit": limit,
            }
        )
        return self.host_result


class FakeImpact:
    def __init__(self):
        self.calls = []

    def impact(
        self,
        entity_type,
        entity_id,
        max_depth=None,
    ):
        self.calls.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "max_depth": max_depth,
            }
        )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "direction": "impact",
            "count": 1,
            "max_depth": max_depth,
            "assets": [
                {
                    "entity_type": "application",
                    "entity_id": "himp",
                    "depth": 1,
                    "via_relationship": "runs_on",
                    "path": [],
                }
            ],
        }


def host_dependency(
    hostname,
    host_analysis,
    depth=1,
):
    return {
        "hostname": hostname,
        "depth": depth,
        "path": [
            {
                "source_type": "application",
                "source_id": "himp",
                "relationship_type": "runs_on",
                "target_type": "host",
                "target_id": hostname,
            }
        ],
        "history_available": host_analysis[
            "history_available"
        ],
        "analysis": host_analysis,
    }


def make_service(
    *,
    hosts=None,
    host_result=None,
):
    health = FakeHealth(
        hosts=hosts,
        host_result=host_result,
    )
    impact = FakeImpact()

    service = RemediationRecommendationService(
        health=health,
        impact=impact,
    )

    return service, health, impact


def test_unhealthy_dependency_creates_evidence_backed_recommendation():
    unhealthy = analysis(
        current_status="FAIL",
        current_state="UNHEALTHY",
        observation_count=4,
        current_streak=2,
        failure_percentage=50.0,
        unhealthy_percentage=75.0,
    )

    service, _, impact = make_service(
        hosts=[
            host_dependency(
                "himpdb01.server.arpa",
                unhealthy,
                depth=2,
            )
        ]
    )

    result = service.recommend(
        "application",
        "himp",
    )

    assert result["recommendation_count"] == 1
    assert result["execution_performed"] is False

    recommendation = result[
        "recommendations"
    ][0]

    assert recommendation["condition"] == (
        "HOST_UNHEALTHY"
    )
    assert recommendation["severity"] == (
        "CRITICAL"
    )
    assert recommendation["target"] == {
        "entity_type": "host",
        "entity_id": "himpdb01.server.arpa",
    }
    assert recommendation[
        "dependency_depth"
    ] == 2
    assert recommendation["evidence"][
        "failure_percentage"
    ] == 50.0
    assert recommendation["automation"] is None
    assert recommendation[
        "execution_permitted"
    ] is False
    assert recommendation[
        "affected_assets"
    ][0]["entity_id"] == "himp"

    assert impact.calls == [
        {
            "entity_type": "host",
            "entity_id": "himpdb01.server.arpa",
            "max_depth": None,
        }
    ]


def test_warning_state_uses_warning_severity():
    unhealthy = analysis(
        current_status="WARNING",
        current_state="UNHEALTHY",
        observation_count=3,
        failure_percentage=0.0,
        unhealthy_percentage=33.33,
    )

    service, _, _ = make_service(
        hosts=[
            host_dependency(
                "pve01",
                unhealthy,
            )
        ]
    )

    result = service.recommend(
        "application",
        "example",
    )

    assert result["recommendations"][0][
        "severity"
    ] == "WARNING"


def test_flapping_host_creates_stability_recommendation():
    flapping = analysis(
        current_status="PASS",
        current_state="HEALTHY",
        transition_count=4,
        flap_count=3,
        is_flapping=True,
    )

    service, _, _ = make_service(
        hosts=[
            host_dependency(
                "pve01",
                flapping,
            )
        ]
    )

    result = service.recommend(
        "application",
        "example",
    )

    assert result["recommendation_count"] == 1
    assert result["recommendations"][0][
        "condition"
    ] == "HOST_FLAPPING"
    assert result["recommendations"][0][
        "severity"
    ] == "WARNING"


def test_unhealthy_flapping_host_can_create_two_distinct_findings():
    unhealthy_flapping = analysis(
        current_status="FAIL",
        current_state="UNHEALTHY",
        transition_count=4,
        flap_count=3,
        is_flapping=True,
        failure_percentage=60.0,
        unhealthy_percentage=80.0,
    )

    service, _, _ = make_service(
        hosts=[
            host_dependency(
                "pve01",
                unhealthy_flapping,
            )
        ]
    )

    result = service.recommend(
        "application",
        "example",
    )

    assert {
        item["condition"]
        for item in result["recommendations"]
    } == {
        "HOST_UNHEALTHY",
        "HOST_FLAPPING",
    }


def test_healthy_host_produces_no_recommendation():
    service, _, impact = make_service(
        hosts=[
            host_dependency(
                "automation.server.arpa",
                analysis(),
            )
        ]
    )

    result = service.recommend(
        "application",
        "himp",
    )

    assert result["recommendation_count"] == 0
    assert result["recommendations"] == []
    assert impact.calls == []


def test_history_unavailable_does_not_invent_recommendation():
    unknown = analysis(
        history_available=False,
        current_status=None,
        current_state="UNKNOWN",
        observation_count=0,
        current_streak=0,
    )

    service, _, impact = make_service(
        hosts=[
            host_dependency(
                "unknown.server.arpa",
                unknown,
            )
        ]
    )

    result = service.recommend(
        "application",
        "example",
    )

    assert result["recommendations"] == []
    assert impact.calls == []


def test_host_root_uses_its_own_health_history():
    unhealthy = analysis(
        current_status="FAIL",
        current_state="UNHEALTHY",
        failure_percentage=100.0,
        unhealthy_percentage=100.0,
    )

    service, health, _ = make_service(
        host_result={
            "kind": "host",
            "hostname": "pve01",
            "limit": 25,
            "analysis": unhealthy,
        }
    )

    result = service.recommend(
        "host",
        "pve01",
        limit=25,
    )

    assert result["recommendation_count"] == 1
    assert result["recommendations"][0][
        "dependency_depth"
    ] == 0

    assert health.host_calls == [
        {
            "hostname": "pve01",
            "limit": 25,
        }
    ]


def test_host_dependency_is_not_analyzed_twice_as_root():
    unhealthy = analysis(
        current_status="FAIL",
        current_state="UNHEALTHY",
        failure_percentage=100.0,
        unhealthy_percentage=100.0,
    )

    service, health, _ = make_service(
        hosts=[
            host_dependency(
                "pve01",
                unhealthy,
                depth=1,
            )
        ],
        host_result={
            "kind": "host",
            "hostname": "pve01",
            "limit": 100,
            "analysis": unhealthy,
        },
    )

    result = service.recommend(
        "host",
        "pve01",
    )

    assert result["recommendation_count"] == 1
    assert health.host_calls == []


def test_recommendations_are_deterministically_sorted():
    warning = analysis(
        current_status="WARNING",
        current_state="UNHEALTHY",
    )
    critical = analysis(
        current_status="FAIL",
        current_state="UNHEALTHY",
        failure_percentage=100.0,
    )

    service, _, _ = make_service(
        hosts=[
            host_dependency(
                "z-host",
                warning,
            ),
            host_dependency(
                "a-host",
                critical,
            ),
        ]
    )

    result = service.recommend(
        "application",
        "example",
    )

    assert [
        item["target"]["entity_id"]
        for item in result["recommendations"]
    ] == [
        "a-host",
        "z-host",
    ]


def test_recommendation_generation_never_executes_automation():
    unhealthy = analysis(
        current_status="FAIL",
        current_state="UNHEALTHY",
        failure_percentage=100.0,
    )

    service, _, _ = make_service(
        hosts=[
            host_dependency(
                "pve01",
                unhealthy,
            )
        ]
    )

    result = service.recommend(
        "application",
        "example",
    )

    assert result["execution_performed"] is False
    assert all(
        item["execution_permitted"] is False
        for item in result["recommendations"]
    )
    assert all(
        item["automation"] is None
        for item in result["recommendations"]
    )
