import pytest

from himp.services.inventory import InventoryService
from himp.services.inventory_writer import InventoryFileWriter


def save_host(repository, hostname, group):
    repository.save_host({
        "hostname": hostname,
        "group": group,
        "ip": "192.0.2.1",
        "user": "operator",
        "become": False,
    })


def test_rename_group_preserves_inactive_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "inventory.db"))
    inventory = tmp_path / "hosts.yml"
    inventory.write_text(
        "all:\n"
        "  children:\n"
        "    old:\n"
        "      hosts:\n"
        "        live:\n"
        "          ansible_host: 192.0.2.1\n"
    )
    service = InventoryService()
    service.writer = InventoryFileWriter(inventory)
    for hostname, group in [("live", "old"), ("retired", "old"), ("other", "backup")]:
        save_host(service.repository, hostname, group)
    service.repository.mark_removed("retired")

    result = service.rename_group("old", "new")

    assert result["group"] == "new"
    assert service.find_host("live")["group_name"] == "new"
    assert service.find_host("other")["group_name"] == "backup"
    assert service.find_host("retired") is None
    retired = service.repository.find_host("retired", include_inactive=True)
    assert retired["group_name"] == "new"
    assert "retired:" not in inventory.read_text()
    assert {
        change["hostname"] for change in service.changes()
        if change["change_type"] == "UPDATED" and change["field"] == "group_name"
    } == {"live", "retired"}


def test_sync_counts_membership_drift_before_reconciliation(tmp_path, monkeypatch):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "inventory.db"))
    service = InventoryService()
    inventory = tmp_path / "hosts.yml"
    inventory.write_text("all: {}\n")
    service.writer = InventoryFileWriter(inventory)
    host = {
        "hostname": "added",
        "group": "new",
        "ip": "192.0.2.2",
        "user": "operator",
        "become": False,
    }
    monkeypatch.setattr(service.collector, "hosts", lambda: [host])

    result = service.sync()

    assert result["membership_drift_count"] == 1
    assert result["active_hosts"] == 1
    assert service.sync()["membership_drift_count"] == 0


    monkeypatch.setattr(service.collector, "hosts", lambda: [])
    with pytest.raises(ValueError, match="omitted 1 active host"):
        service.sync()
    assert service.find_host("added") is not None
