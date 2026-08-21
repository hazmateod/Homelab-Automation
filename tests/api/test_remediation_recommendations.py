from fastapi.testclient import TestClient

from himp.api import remediation


class FakeRecommendationService:
    def __init__(self):
        self.calls = []

    def recommend(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        self.calls.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "limit": limit,
            }
        )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "recommendation_count": 0,
            "execution_performed": False,
            "recommendations": [],
        }


def test_recommendation_api_delegates_to_service():
    fake = FakeRecommendationService()

    original = (
        remediation.remediation_recommendation_service
    )
    remediation.remediation_recommendation_service = (
        fake
    )

    try:
        result = remediation.remediation_recommendations(
            entity_type="application",
            entity_id="himp",
            limit=25,
        )
    finally:
        remediation.remediation_recommendation_service = (
            original
        )

    assert result["recommendation_count"] == 0

    assert fake.calls == [
        {
            "entity_type": "application",
            "entity_id": "himp",
            "limit": 25,
        }
    ]


def test_recommendation_route_is_registered():
    from himp.api import server

    paths = set(
        server.app.openapi()["paths"]
    )

    assert (
        "/api/remediation/recommendations/"
        "{entity_type}/{entity_id}"
    ) in paths


def test_recommendation_route_requires_session():
    from himp.api import server

    with TestClient(server.app) as client:
        response = client.get(
            "/api/remediation/recommendations/"
            "application/himp"
        )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required"
    }


def test_recommendation_limit_is_bounded_by_api():
    from himp.api import server

    with TestClient(server.app) as client:
        response = client.get(
            "/api/remediation/recommendations/"
            "application/himp?limit=0"
        )

    assert response.status_code in {
        401,
        422,
    }
