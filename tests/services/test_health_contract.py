from types import SimpleNamespace

from himp.health.models import (
    HealthCheckResult,
    HealthSource,
    HealthStatus,
)
from himp.services.health_cards import HealthCardsService
from himp.services.host_health_dashboard import (
    HostHealthDashboardService,
)


def test_health_check_result_defaults_to_plugin_source():
    result = HealthCheckResult(
        plugin="infrastructure",
        check="health",
        status=HealthStatus.PASS,
        message="PASS",
    )

    assert result.source is HealthSource.PLUGIN


def test_health_check_result_supports_host_connectivity_source():
    result = HealthCheckResult(
        plugin="host",
        check="ssh",
        status=HealthStatus.PASS,
        source=HealthSource.HOST_CONNECTIVITY,
        message="SSH authentication successful.",
    )

    assert result.source is HealthSource.HOST_CONNECTIVITY


class FakeInventory:
    def all_hosts(self):
        return [
            {
                "hostname": "pve01",
                "group_name": "proxmox",
                "ip": "192.168.1.10",
                "ansible_user": "root",
            }
        ]


class FakeHostHealth:
    def latest(
        self,
        hostname,
        check=None,
    ):
        assert hostname == "pve01"

        return {
            "status": "PASS",
            "check_name": "ssh",
            "message": "SSH authentication successful.",
            "duration_ms": 25.0,
            "created_at": "2026-08-20 00:00:00",
            "details": {},
        }

    def host(
        self,
        hostname,
        limit=50,
    ):
        return []

    def history(
        self,
        limit=50,
    ):
        return []


def test_host_health_dashboard_declares_connectivity_source():
    service = HostHealthDashboardService()
    service.inventory = FakeInventory()
    service.health = FakeHostHealth()

    summary = service.summary()

    assert summary["source"] == "HOST_CONNECTIVITY"
    assert summary["label"] == "Host Connectivity"

    assert summary["hosts"][0]["source"] == (
        "HOST_CONNECTIVITY"
    )


class FakeHealthRepository:
    def plugins(self):
        return [
            SimpleNamespace(
                summary=SimpleNamespace(
                    plugin="infrastructure",
                    status=HealthStatus.FAIL,
                    score=4,
                    possible=8,
                ),
                hosts=[
                    object(),
                ],
            )
        ]


def test_health_cards_use_normalized_plugin_health_contract():
    service = HealthCardsService()
    service.repository = FakeHealthRepository()

    assert service.summary() == {
        "source": "PLUGIN",
        "label": "Plugin Health",
        "cards": [
            {
                "source": "PLUGIN",
                "plugin": "infrastructure",
                "status": "FAIL",
                "earned": 4,
                "possible": 8,
                "hosts": 1,
            }
        ],
    }


def test_health_cards_preserve_normalized_failure_status():
    service = HealthCardsService()
    service.repository = FakeHealthRepository()

    cards = service.all()

    assert cards[0]["status"] == "FAIL"
