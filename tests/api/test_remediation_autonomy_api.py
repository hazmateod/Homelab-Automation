from datetime import datetime

from fastapi.testclient import (
    TestClient,
)

from himp.api import remediation
from himp.api import server
from himp.api.dependencies import (
    require_session,
)
from himp.services.sessions import (
    SessionResult,
)


def authenticated_session():
    now = datetime(
        2026,
        8,
        21,
        15,
        0,
    )

    return SessionResult(
        success=True,
        username="operator",
        role="user",
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )


class FakeRecommendationService:
    def recommend(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "recommendation_count": 1,
            "execution_performed": False,
            "recommendations": [
                {
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
                    "automation": None,
                    "execution_permitted":
                        False,
                    "autonomy": {
                        "decision":
                            "REQUIRE_APPROVAL",
                        "automatic_execution_permitted":
                            False,
                        "recommendation_id":
                            "HOST_UNHEALTHY:pve01",
                        "condition":
                            "HOST_UNHEALTHY",
                        "task_id":
                            None,
                        "target_type":
                            "host",
                        "target_id":
                            "pve01",
                        "risk_level":
                            None,
                        "reason":
                            (
                                "Recommendation has no "
                                "explicit automation mapping."
                            ),
                    },
                }
            ],
        }


def test_recommendation_api_exposes_autonomy_decision(
    monkeypatch,
):
    monkeypatch.setattr(
        remediation,
        "remediation_recommendation_service",
        FakeRecommendationService(),
    )

    server.app.dependency_overrides[
        require_session
    ] = authenticated_session

    try:
        with TestClient(
            server.app
        ) as client:
            response = client.get(
                "/api/remediation/"
                "recommendations/"
                "application/himp"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200

    payload = response.json()

    assert payload[
        "execution_performed"
    ] is False

    item = payload[
        "recommendations"
    ][0]

    assert item[
        "autonomy"
    ]["decision"] == (
        "REQUIRE_APPROVAL"
    )

    assert (
        item[
            "autonomy"
        ][
            "automatic_execution_permitted"
        ]
        is False
    )

    assert item[
        "execution_permitted"
    ] is False
