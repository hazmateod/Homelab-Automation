import pytest

from himp.api import health_history
from himp.api import health_trends


def test_health_history_returns_summary_and_history(
    monkeypatch,
):
    expected_history = [
        {
            "plugin": "proxmox",
            "status": "PASS",
            "score": 100,
            "possible": 100,
        },
        {
            "plugin": "pbs",
            "status": "WARNING",
            "score": 75,
            "possible": 100,
        },
    ]

    class FakeHistoryService:
        def summary(self):
            return {
                "records": 2,
                "plugins": 2,
            }

        def history(self):
            return expected_history

    monkeypatch.setattr(
        health_history,
        "history",
        FakeHistoryService(),
    )

    response = health_history.health_history()

    assert response.status_code == 200
    assert response.body

    import json

    payload = json.loads(
        response.body
    )

    assert payload == {
        "summary": {
            "records": 2,
            "plugins": 2,
        },
        "history": expected_history,
    }


def test_plugin_health_history_returns_plugin_history(
    monkeypatch,
):
    expected = [
        {
            "plugin": "proxmox",
            "status": "PASS",
            "score": 100,
        },
        {
            "plugin": "proxmox",
            "status": "WARNING",
            "score": 50,
        },
    ]

    class FakeHistoryService:
        def plugin(self, plugin):
            assert plugin == "proxmox"
            return expected

    monkeypatch.setattr(
        health_history,
        "history",
        FakeHistoryService(),
    )

    response = health_history.plugin_health_history(
        "proxmox"
    )

    assert response.status_code == 200

    import json

    payload = json.loads(
        response.body
    )

    assert payload == {
        "plugin": "proxmox",
        "history": expected,
    }


def test_health_trends_returns_summary(
    monkeypatch,
):
    expected = {
        "plugins": 2,
        "healthy": 1,
        "warnings": 1,
        "failed": 0,
        "trends": [
            {
                "plugin": "proxmox",
                "status": "PASS",
                "score": 100,
            },
            {
                "plugin": "pbs",
                "status": "WARNING",
                "score": 50,
            },
        ],
    }

    class FakeTrendsService:
        def summary(self):
            return expected

    monkeypatch.setattr(
        health_trends,
        "trends",
        FakeTrendsService(),
    )

    response = health_trends.health_trends()

    assert response.status_code == 200

    import json

    payload = json.loads(
        response.body
    )

    assert payload == expected


def test_plugin_health_trends_returns_trend(
    monkeypatch,
):
    expected = {
        "plugin": "proxmox",
        "status": "PASS",
        "score": 100,
        "possible": 100,
        "latest": "2026-08-11T02:00:00",
        "trend": [
            {
                "created_at": "2026-08-10T02:00:00",
                "score": 75,
                "status": "WARNING",
            },
            {
                "created_at": "2026-08-11T02:00:00",
                "score": 100,
                "status": "PASS",
            },
        ],
    }

    class FakeTrendsService:
        def plugin(self, plugin):
            assert plugin == "proxmox"
            return expected

    monkeypatch.setattr(
        health_trends,
        "trends",
        FakeTrendsService(),
    )

    response = health_trends.plugin_health_trends(
        "proxmox"
    )

    assert response.status_code == 200

    import json

    payload = json.loads(
        response.body
    )

    assert payload == expected


def test_plugin_health_trends_missing_returns_empty_object(
    monkeypatch,
):
    class FakeTrendsService:
        def plugin(self, plugin):
            assert plugin == "missing"
            return None

    monkeypatch.setattr(
        health_trends,
        "trends",
        FakeTrendsService(),
    )

    response = health_trends.plugin_health_trends(
        "missing"
    )

    assert response.status_code == 200

    import json

    payload = json.loads(
        response.body
    )

    assert payload == {}


def test_health_history_service_uses_default_limit(
    monkeypatch,
):
    calls = []

    class FakeRepository:
        def history(self, limit):
            calls.append(limit)
            return []

    from himp.services.health_history import (
        HealthHistoryService,
    )

    service = HealthHistoryService()

    monkeypatch.setattr(
        service,
        "repository",
        FakeRepository(),
    )

    result = service.history()

    assert result == []
    assert calls == [50]
