import pytest

from himp.api import inventory


class FakeInventoryService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def rename_group(self, group, new_group):
        self.calls.append((group, new_group))

        if self.error:
            raise self.error

        return self.result


def test_update_inventory_group_success(monkeypatch):
    service = FakeInventoryService(
        result={
            "previous_group": "proxmox",
            "group": "proxmox-production",
        }
    )

    monkeypatch.setattr(
        inventory,
        "service",
        service,
    )

    request = inventory.InventoryGroupUpdate(
        new_group="proxmox-production",
    )

    result = __import__(
        "asyncio"
    ).run(
        inventory.update_inventory_group(
            "proxmox",
            request,
        )
    )

    assert result == {
        "group": {
            "previous_group": "proxmox",
            "group": "proxmox-production",
        },
        "message": "Inventory group updated successfully.",
    }

    assert service.calls == [
        ("proxmox", "proxmox-production"),
    ]


def test_update_inventory_group_missing_group_returns_404(
    monkeypatch,
):
    service = FakeInventoryService(
        error=ValueError(
            "Inventory group does not exist: missing"
        )
    )

    monkeypatch.setattr(
        inventory,
        "service",
        service,
    )

    request = inventory.InventoryGroupUpdate(
        new_group="new-group",
    )

    with pytest.raises(inventory.HTTPException) as exc:
        __import__(
            "asyncio"
        ).run(
            inventory.update_inventory_group(
                "missing",
                request,
            )
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == {
        "error":
            "Inventory group does not exist: missing"
    }


def test_update_inventory_group_duplicate_returns_409(
    monkeypatch,
):
    service = FakeInventoryService(
        error=ValueError(
            "Inventory group already exists: backup"
        )
    )

    monkeypatch.setattr(
        inventory,
        "service",
        service,
    )

    request = inventory.InventoryGroupUpdate(
        new_group="backup",
    )

    with pytest.raises(inventory.HTTPException) as exc:
        __import__(
            "asyncio"
        ).run(
            inventory.update_inventory_group(
                "proxmox",
                request,
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == {
        "error":
            "Inventory group already exists: backup"
    }


def test_update_inventory_group_invalid_name_returns_400(
    monkeypatch,
):
    service = FakeInventoryService(
        error=ValueError(
            "Inventory group name cannot be empty"
        )
    )

    monkeypatch.setattr(
        inventory,
        "service",
        service,
    )

    request = inventory.InventoryGroupUpdate(
        new_group="   ",
    )

    with pytest.raises(inventory.HTTPException) as exc:
        __import__(
            "asyncio"
        ).run(
            inventory.update_inventory_group(
                "proxmox",
                request,
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "error":
            "Inventory group name cannot be empty"
    }
