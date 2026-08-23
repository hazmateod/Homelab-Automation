from types import SimpleNamespace

from himp.commands import inventory_sync


class SuccessfulInventoryService:
    def sync(self):
        return {
            "synced": 43,
            "active_hosts": 43,
            "total_hosts": 43,
            "recent_changes": 2,
        }


class FailedInventoryService:
    def sync(self):
        raise RuntimeError(
            "inventory synchronization failed"
        )


def test_inventory_sync_closes_postgresql_pools_on_success(
    monkeypatch,
):
    close_calls = []

    monkeypatch.setattr(
        inventory_sync,
        "InventoryService",
        SuccessfulInventoryService,
    )

    monkeypatch.setattr(
        inventory_sync.PostgreSQLDatabase,
        "close_pools",
        lambda: close_calls.append(True),
    )

    result = inventory_sync.run(
        SimpleNamespace()
    )

    assert result == 0
    assert close_calls == [True]


def test_inventory_sync_closes_postgresql_pools_on_sync_failure(
    monkeypatch,
):
    close_calls = []

    monkeypatch.setattr(
        inventory_sync,
        "InventoryService",
        FailedInventoryService,
    )

    monkeypatch.setattr(
        inventory_sync.PostgreSQLDatabase,
        "close_pools",
        lambda: close_calls.append(True),
    )

    result = inventory_sync.run(
        SimpleNamespace()
    )

    assert result == 1
    assert close_calls == [True]


def test_inventory_sync_closes_postgresql_pools_on_service_creation_failure(
    monkeypatch,
):
    close_calls = []

    def fail_service_creation():
        raise RuntimeError(
            "inventory service initialization failed"
        )

    monkeypatch.setattr(
        inventory_sync,
        "InventoryService",
        fail_service_creation,
    )

    monkeypatch.setattr(
        inventory_sync.PostgreSQLDatabase,
        "close_pools",
        lambda: close_calls.append(True),
    )

    result = inventory_sync.run(
        SimpleNamespace()
    )

    assert result == 1
    assert close_calls == [True]
