from pathlib import Path

import pytest

from himp.services.inventory_writer import InventoryFileWriter


def make_inventory(tmp_path):
    inventory = tmp_path / "hosts.yml"

    inventory.write_text(
        """all:
  children:
    proxmox:
      hosts:
        pve01:
          ansible_host: 10.10.37.50
          ansible_user: root
    backup:
      hosts:
        pbs01:
          ansible_host: 10.10.37.52
          ansible_user: root
"""
    )

    return inventory


def test_rename_group_preserves_hosts_and_yaml_structure(
    tmp_path,
):
    inventory = make_inventory(tmp_path)

    writer = InventoryFileWriter(
        filename=inventory,
    )

    result = writer.rename_group(
        "proxmox",
        "proxmox-production",
    )

    assert result == {
        "previous_group": "proxmox",
        "group": "proxmox-production",
    }

    content = inventory.read_text()

    assert "proxmox:" not in content
    assert "proxmox-production:" in content
    assert "pve01:" in content
    assert "backup:" in content
    assert "pbs01:" in content


def test_rename_group_rejects_missing_group(
    tmp_path,
):
    inventory = make_inventory(tmp_path)

    writer = InventoryFileWriter(
        filename=inventory,
    )

    with pytest.raises(
        ValueError,
        match="Inventory group does not exist",
    ):
        writer.rename_group(
            "missing",
            "new-group",
        )


def test_rename_group_rejects_empty_destination(
    tmp_path,
):
    inventory = make_inventory(tmp_path)

    writer = InventoryFileWriter(
        filename=inventory,
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        writer.rename_group(
            "proxmox",
            "   ",
        )


def test_rename_group_rejects_duplicate_destination(
    tmp_path,
):
    inventory = make_inventory(tmp_path)

    writer = InventoryFileWriter(
        filename=inventory,
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        writer.rename_group(
            "proxmox",
            "backup",
        )


def test_rename_group_same_name_is_noop(
    tmp_path,
):
    inventory = make_inventory(tmp_path)
    original = inventory.read_text()

    writer = InventoryFileWriter(
        filename=inventory,
    )

    result = writer.rename_group(
        "proxmox",
        "proxmox",
    )

    assert result == {
        "previous_group": "proxmox",
        "group": "proxmox",
    }

    assert inventory.read_text() == original


def test_rename_group_preserves_unrelated_inventory_text(
    tmp_path,
):
    inventory = make_inventory(tmp_path)
    original = inventory.read_text()

    writer = InventoryFileWriter(
        filename=inventory,
    )

    writer.rename_group(
        "backup",
        "backup-production",
    )

    updated = inventory.read_text()

    assert "pve01:" in updated
    assert "pbs01:" in updated
    assert "proxmox:" in updated
    assert "backup-production:" in updated
    assert "backup:" not in updated

    assert updated.count("pve01:") == original.count(
        "pve01:"
    )
