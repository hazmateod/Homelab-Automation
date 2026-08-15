import sqlite3

from himp.services.inventory_baseline import (
    InventoryBaselineService,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor

    def query(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        return cursor.fetchall()


def host(
    hostname="pve01",
    group="proxmox",
    ip="192.168.10.51",
    user="root",
    become=False,
):
    return {
        "hostname": hostname,
        "group": group,
        "ip": ip,
        "user": user,
        "become": become,
    }


def test_baseline_detects_no_drift_when_inventory_matches():
    class FakeInventoryRepository:
        def all_hosts(self):
            return [
                host(),
            ]

    class FakeBaselineRepository:
        def create(self, name, hosts):
            assert name == "production"
            assert hosts == [
                host(),
            ]

        def find(self, name):
            assert name == "production"
            return {
                "name": "production",
                "hosts": [
                    host(),
                ],
            }

    service = InventoryBaselineService(
        inventory=FakeInventoryRepository(),
        repository=FakeBaselineRepository(),
    )

    result = service.compare(
        "production"
    )

    assert result == {
        "baseline": "production",
        "drift": [],
    }


def test_baseline_detects_changed_host_field():
    class FakeInventoryRepository:
        def all_hosts(self):
            return [
                host(
                    ip="192.168.10.52",
                ),
            ]

    class FakeBaselineRepository:
        def find(self, name):
            return {
                "name": "production",
                "hosts": [
                    host(),
                ],
            }

    service = InventoryBaselineService(
        inventory=FakeInventoryRepository(),
        repository=FakeBaselineRepository(),
    )

    result = service.compare(
        "production"
    )

    assert result["baseline"] == "production"
    assert result["drift"] == [
        {
            "hostname": "pve01",
            "field": "ip",
            "expected": "192.168.10.51",
            "actual": "192.168.10.52",
            "drift_type": "CHANGED",
        },
    ]


def test_baseline_detects_added_host():
    class FakeInventoryRepository:
        def all_hosts(self):
            return [
                host(),
                host(
                    hostname="pve02",
                    ip="192.168.10.52",
                ),
            ]

    class FakeBaselineRepository:
        def find(self, name):
            return {
                "name": "production",
                "hosts": [
                    host(),
                ],
            }

    service = InventoryBaselineService(
        inventory=FakeInventoryRepository(),
        repository=FakeBaselineRepository(),
    )

    result = service.compare(
        "production"
    )

    assert result["drift"] == [
        {
            "hostname": "pve02",
            "field": None,
            "expected": None,
            "actual": {
                "group": "proxmox",
                "ip": "192.168.10.52",
                "user": "root",
                "become": False,
            },
            "drift_type": "ADDED",
        },
    ]


def test_baseline_detects_removed_host():
    class FakeInventoryRepository:
        def all_hosts(self):
            return []

    class FakeBaselineRepository:
        def find(self, name):
            return {
                "name": "production",
                "hosts": [
                    host(),
                ],
            }

    service = InventoryBaselineService(
        inventory=FakeInventoryRepository(),
        repository=FakeBaselineRepository(),
    )

    result = service.compare(
        "production"
    )

    assert result["drift"] == [
        {
            "hostname": "pve01",
            "field": None,
            "expected": {
                "group": "proxmox",
                "ip": "192.168.10.51",
                "user": "root",
                "become": False,
            },
            "actual": None,
            "drift_type": "REMOVED",
        },
    ]


def test_baseline_reports_unknown_baseline():
    class FakeInventoryRepository:
        def all_hosts(self):
            return []

    class FakeBaselineRepository:
        def find(self, name):
            return None

    service = InventoryBaselineService(
        inventory=FakeInventoryRepository(),
        repository=FakeBaselineRepository(),
    )

    try:
        service.compare("missing")
    except ValueError as error:
        assert str(error) == (
            "Inventory baseline not found: missing"
        )
    else:
        raise AssertionError(
            "Expected missing baseline to raise ValueError"
        )
