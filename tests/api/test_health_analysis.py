from fastapi import FastAPI
from fastapi.testclient import TestClient

from himp.api import health_analysis as api


class FakeHealthAnalysisService:
    def plugin(
        self,
        plugin,
        limit=100,
    ):
        if plugin == "missing":
            return None

        return {
            "kind": "plugin",
            "plugin": plugin,
            "limit": limit,
            "analysis": {
                "observation_count": 4,
            },
        }

    def host(
        self,
        hostname,
        limit=100,
    ):
        if hostname == "missing":
            return None

        return {
            "kind": "host",
            "hostname": hostname,
            "limit": limit,
            "analysis": {
                "observation_count": 100,
            },
        }

    def correlate(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "limit": limit,
            "host_count": 2,
            "unhealthy_hosts": 0,
            "flapping_hosts": 0,
            "hosts": [],
        }


def make_client():
    app = FastAPI()

    api.analysis_service = (
        FakeHealthAnalysisService()
    )

    app.include_router(
        api.router,
        prefix="/api",
    )

    return TestClient(
        app
    )


def test_plugin_analysis_api():
    client = make_client()

    response = client.get(
        "/api/health/analysis/plugins/technitium"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["plugin"] == "technitium"
    assert body["limit"] == 100


def test_plugin_analysis_missing_returns_404():
    client = make_client()

    response = client.get(
        "/api/health/analysis/plugins/missing"
    )

    assert response.status_code == 404


def test_host_analysis_api():
    client = make_client()

    response = client.get(
        "/api/health/analysis/hosts/pbs01",
        params={
            "limit": 250,
        },
    )

    assert response.status_code == 200
    assert response.json()["limit"] == 250


def test_host_analysis_missing_returns_404():
    client = make_client()

    response = client.get(
        "/api/health/analysis/hosts/missing"
    )

    assert response.status_code == 404


def test_correlation_analysis_api():
    client = make_client()

    response = client.get(
        "/api/health/analysis/correlation/"
        "application/himp"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["host_count"] == 2
    assert body["entity_type"] == "application"


def test_analysis_api_rejects_invalid_limit():
    client = make_client()

    response = client.get(
        "/api/health/analysis/hosts/pbs01",
        params={
            "limit": 0,
        },
    )

    assert response.status_code == 422
