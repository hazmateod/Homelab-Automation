import pytest

from fastapi import HTTPException

from himp.api import host_health


def test_check_host_health_returns_results(
    monkeypatch,
):
    expected = [
        {
            "hostname": "pve01",
            "results": [
                {
                    "status": "PASS",
                },
            ],
        },
        {
            "hostname": "pve02",
            "results": [
                {
                    "status": "PASS",
                },
            ],
        },
    ]

    class FakeHealthService:
        def check_hosts(self, hostnames):
            assert hostnames == [
                "pve01",
                "pve02",
            ]
            return expected

    monkeypatch.setattr(
        host_health,
        "health",
        FakeHealthService(),
    )

    request = host_health.HostHealthCheckRequest(
        hostnames=[
            "pve01",
            "pve02",
        ],
    )

    response = host_health.check_host_health(
        request
    )

    assert response["count"] == 2
    assert response["results"] == expected


def test_check_host_health_missing_host_returns_404(
    monkeypatch,
):
    class FakeHealthService:
        def check_hosts(self, hostnames):
            assert hostnames == ["missing"]
            raise ValueError(
                "Inventory host not found: missing"
            )

    monkeypatch.setattr(
        host_health,
        "health",
        FakeHealthService(),
    )

    request = host_health.HostHealthCheckRequest(
        hostnames=["missing"],
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        host_health.check_host_health(
            request
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == {
        "error": "Inventory host not found: missing",
    }


def test_check_host_health_requires_at_least_one_hostname():
    with pytest.raises(ValueError):
        host_health.HostHealthCheckRequest(
            hostnames=[]
        )


def test_host_health_summary_returns_dashboard_summary(
    monkeypatch,
):
    expected = {
        "total": 2,
        "passed": 1,
        "warnings": 0,
        "failed": 1,
        "unknown": 0,
        "score": 50,
        "hosts": [],
        "failures": [],
        "trends": [],
    }

    class FakeDashboardService:
        def summary(self):
            return expected

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_summary()

    assert response == expected


def test_host_health_history_returns_history_with_default_limit(
    monkeypatch,
):
    expected = [
        {
            "hostname": "pve01",
            "status": "PASS",
        },
    ]

    class FakeDashboardService:
        def history(self, hostname, limit):
            assert hostname is None
            assert limit == 50
            return expected

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_history(limit=50)

    assert response == {
        "history": expected,
    }


def test_host_health_history_passes_custom_limit(
    monkeypatch,
):
    expected = [
        {
            "hostname": "pve01",
            "status": "PASS",
        },
    ]

    class FakeDashboardService:
        def history(self, hostname, limit):
            assert hostname is None
            assert limit == 25
            return expected

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_history(
        limit=25
    )

    assert response == {
        "history": expected,
    }


def test_host_health_trends_returns_dashboard_trends(
    monkeypatch,
):
    expected = [
        {
            "hostname": "pve01",
            "status": "PASS",
            "trend": [],
        },
    ]

    class FakeDashboardService:
        def trends(self, limit):
            assert limit == 10
            return expected

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_trends(limit=10)

    assert response == {
        "trends": expected,
    }


def test_host_health_trends_passes_custom_limit(
    monkeypatch,
):
    expected = [
        {
            "hostname": "pve01",
            "status": "PASS",
            "trend": [],
        },
    ]

    class FakeDashboardService:
        def trends(self, limit):
            assert limit == 5
            return expected

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_trends(
        limit=5
    )

    assert response == {
        "trends": expected,
    }


def test_host_health_host_returns_matching_host(
    monkeypatch,
):
    hosts = [
        {
            "hostname": "pve01",
            "status": "PASS",
            "score": 100,
        },
        {
            "hostname": "pve02",
            "status": "FAIL",
            "score": 0,
        },
    ]

    class FakeDashboardService:
        def hosts(self):
            return hosts

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_host(
        "pve02"
    )

    assert response == hosts[1]


def test_host_health_host_missing_returns_404(
    monkeypatch,
):
    class FakeDashboardService:
        def hosts(self):
            return [
                {
                    "hostname": "pve01",
                    "status": "PASS",
                },
            ]

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        host_health.host_health_host(
            "missing"
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == (
        "Inventory host not found"
    )


def test_host_health_host_history_returns_history(
    monkeypatch,
):
    expected = [
        {
            "status": "PASS",
            "created_at": "2026-08-11T02:00:00",
        },
    ]

    class FakeDashboardService:
        def current(self, hostname):
            assert hostname == "pve01"
            return {
                "hostname": "pve01",
                "status": "PASS",
            }

        def history(self, hostname, limit):
            assert hostname == "pve01"
            assert limit == 50
            return expected

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_host_history(
        "pve01",
        limit=50,
    )

    assert response == {
        "hostname": "pve01",
        "history": expected,
    }


def test_host_health_host_history_passes_custom_limit(
    monkeypatch,
):
    expected = [
        {
            "status": "PASS",
        },
    ]

    class FakeDashboardService:
        def current(self, hostname):
            return {
                "hostname": hostname,
                "status": "PASS",
            }

        def history(self, hostname, limit):
            assert hostname == "pve01"
            assert limit == 10
            return expected

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    response = host_health.host_health_host_history(
        "pve01",
        limit=10,
    )

    assert response == {
        "hostname": "pve01",
        "history": expected,
    }


def test_host_health_host_history_missing_returns_404(
    monkeypatch,
):
    class FakeDashboardService:
        def current(self, hostname):
            assert hostname == "missing"
            return None

    monkeypatch.setattr(
        host_health,
        "dashboard",
        FakeDashboardService(),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        host_health.host_health_host_history(
            "missing"
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == (
        "Inventory host not found"
    )
