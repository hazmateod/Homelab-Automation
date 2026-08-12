import pytest

from fastapi import HTTPException

from types import SimpleNamespace

from himp.api import health


def test_health_summary_returns_serialized_summary(
    monkeypatch,
):
    plugin = SimpleNamespace(
        plugin="disk_health",
        status=SimpleNamespace(
            value="passed"
        ),
        message="Disk health check passed",
        duration_ms=12.5,
        details={
            "usage_percent": 42,
        },
    )

    summary = SimpleNamespace(
        score=100,
        passed=1,
        warnings=0,
        failed=0,
        unknown=0,
        plugins=[plugin],
    )

    class FakeHealthService:
        def summary(self):
            return summary

    monkeypatch.setattr(
        health,
        "service",
        FakeHealthService(),
    )

    import asyncio

    response = asyncio.run(
        health.health_summary()
    )

    assert response == {
        "score": 100,
        "passed": 1,
        "warnings": 0,
        "failed": 0,
        "unknown": 0,
        "plugins": [
            {
                "plugin": "disk_health",
                "status": "passed",
                "message": "Disk health check passed",
                "duration_ms": 12.5,
                "details": {
                    "usage_percent": 42,
                },
            }
        ],
    }


def test_health_all_returns_all_health_results(
    monkeypatch,
):
    expected = [
        {
            "plugin": "disk_health",
            "status": "passed",
            "message": "Disk health check passed",
        },
        {
            "plugin": "network_health",
            "status": "warning",
            "message": "Network latency elevated",
        },
    ]

    class FakeHealthService:
        def all(self):
            return expected

    monkeypatch.setattr(
        health,
        "service",
        FakeHealthService(),
    )

    import asyncio

    response = asyncio.run(
        health.health_all()
    )

    assert response == expected


def test_health_plugin_returns_plugin_result(
    monkeypatch,
):
    expected = {
        "plugin": "disk_health",
        "status": "passed",
        "message": "Disk health check passed",
        "duration_ms": 12.5,
        "details": {
            "usage_percent": 42,
        },
    }

    class FakeHealthService:
        def plugin(self, name):
            assert name == "disk_health"
            return expected

    monkeypatch.setattr(
        health,
        "service",
        FakeHealthService(),
    )

    import asyncio

    response = asyncio.run(
        health.health_plugin(
            "disk_health"
        )
    )

    assert response == expected


def test_health_plugin_missing_returns_404(
    monkeypatch,
):
    class FakeHealthService:
        def plugin(self, name):
            assert name == "missing_plugin"
            return None

    monkeypatch.setattr(
        health,
        "service",
        FakeHealthService(),
    )

    import asyncio

    with pytest.raises(
        HTTPException
    ) as captured:
        asyncio.run(
            health.health_plugin(
                "missing_plugin"
            )
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == (
        "Health plugin not found"
    )
