from fastapi import FastAPI
from fastapi.testclient import TestClient

from himp.api import dependency_impact as api


class FakeDependencyImpactService:
    def dependencies(
        self,
        entity_type,
        entity_id,
        max_depth=None,
    ):
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "direction": "dependencies",
            "count": 2,
            "max_depth": max_depth,
            "assets": [
                {
                    "entity_type": "database",
                    "entity_id": "himp",
                    "depth": 1,
                    "via_relationship": (
                        "depends_on"
                    ),
                    "path": [],
                },
                {
                    "entity_type": "host",
                    "entity_id": (
                        "himpdb01.server.arpa"
                    ),
                    "depth": 2,
                    "via_relationship": (
                        "runs_on"
                    ),
                    "path": [],
                },
            ],
        }

    def impact(
        self,
        entity_type,
        entity_id,
        max_depth=None,
    ):
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "direction": "impact",
            "count": 2,
            "max_depth": max_depth,
            "assets": [
                {
                    "entity_type": "database",
                    "entity_id": "himp",
                    "depth": 1,
                    "via_relationship": (
                        "runs_on"
                    ),
                    "path": [],
                },
                {
                    "entity_type": "application",
                    "entity_id": "himp",
                    "depth": 2,
                    "via_relationship": (
                        "depends_on"
                    ),
                    "path": [],
                },
            ],
        }


def make_client():
    app = FastAPI()

    api.dependency_impact_service = (
        FakeDependencyImpactService()
    )

    app.include_router(
        api.router,
        prefix="/api",
    )

    return TestClient(
        app
    )


def test_dependencies_api():
    client = make_client()

    response = client.get(
        "/api/dependencies/application/himp"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["direction"] == "dependencies"
    assert body["count"] == 2
    assert body["assets"][0]["depth"] == 1


def test_dependencies_api_accepts_max_depth():
    client = make_client()

    response = client.get(
        "/api/dependencies/application/himp",
        params={
            "max_depth": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["max_depth"] == 1


def test_dependencies_api_rejects_invalid_depth():
    client = make_client()

    response = client.get(
        "/api/dependencies/application/himp",
        params={
            "max_depth": 0,
        },
    )

    assert response.status_code == 422


def test_impact_api():
    client = make_client()

    response = client.get(
        "/api/impact/host/"
        "himpdb01.server.arpa"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["direction"] == "impact"
    assert body["count"] == 2

    assert (
        body["assets"][1]["entity_type"]
        == "application"
    )


def test_impact_api_accepts_max_depth():
    client = make_client()

    response = client.get(
        "/api/impact/host/"
        "himpdb01.server.arpa",
        params={
            "max_depth": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["max_depth"] == 1
