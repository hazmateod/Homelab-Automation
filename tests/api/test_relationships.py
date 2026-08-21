from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from himp.api import relationships as api
from himp.api.dependencies import require_admin


@dataclass(frozen=True)
class Relationship:
    source_type: str
    source_id: str
    relationship_type: str
    target_type: str
    target_id: str


class FakeRelationshipService:
    def __init__(self):
        self.relationships = [
            Relationship(
                source_type="application",
                source_id="himp",
                relationship_type=(
                    "depends_on"
                ),
                target_type="database",
                target_id="himp",
            ),
            Relationship(
                source_type="database",
                source_id="himp",
                relationship_type="runs_on",
                target_type="host",
                target_id=(
                    "himpdb01.server.arpa"
                ),
            ),
        ]

    def list(self):
        return self.relationships

    def list_for_source(
        self,
        source_type,
        source_id,
    ):
        return [
            item
            for item in self.relationships
            if (
                item.source_type
                == source_type
                and item.source_id
                == source_id
            )
        ]

    def list_for_target(
        self,
        target_type,
        target_id,
    ):
        return [
            item
            for item in self.relationships
            if (
                item.target_type
                == target_type
                and item.target_id
                == target_id
            )
        ]

    def reconcile(self):
        return {
            "configured": 2,
            "added": 2,
            "removed": 0,
            "unchanged": 0,
            "total": 2,
            "relationships": (
                self.relationships
            ),
        }


def make_client():
    app = FastAPI()

    app.include_router(
        api.router,
        prefix="/api",
    )

    app.dependency_overrides[
        require_admin
    ] = lambda: {
        "role": "admin"
    }

    api.relationship_service = (
        FakeRelationshipService()
    )

    return TestClient(app)


def test_relationship_list_api():
    client = make_client()

    response = client.get(
        "/api/relationships"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 2

    assert (
        body["relationships"][0][
            "relationship_type"
        ]
        == "depends_on"
    )


def test_relationship_source_api():
    client = make_client()

    response = client.get(
        "/api/relationships/source/"
        "application/himp"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 1
    assert (
        body["relationships"][0][
            "target_type"
        ]
        == "database"
    )


def test_relationship_target_api():
    client = make_client()

    response = client.get(
        "/api/relationships/target/"
        "database/himp"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 1
    assert (
        body["relationships"][0][
            "source_id"
        ]
        == "himp"
    )


def test_relationship_reconcile_api():
    client = make_client()

    response = client.post(
        "/api/relationships/reconcile"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["configured"] == 2
    assert body["added"] == 2
    assert body["total"] == 2
