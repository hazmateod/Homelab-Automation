import pytest

from himp.database.host_identity import HostIdentityRepository
from himp.database.inventory import InventoryRepository
from himp.services.inventory_publication import InventoryPublication


def host(name, ip):
    return {
        "hostname": name,
        "group": "fixture",
        "ip": ip,
        "user": "synthetic",
        "become": False,
    }


def test_repeatable_backfill_preserves_identity_through_retirement_and_restore(monkeypatch, tmp_path):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "host-identity.db"))
    inventory = InventoryRepository()
    inventory.save_host(host("current", "192.0.2.1"))
    inventory.save_host(host("retired", "192.0.2.2"))
    inventory.mark_removed("retired")
    identities = HostIdentityRepository(inventory)

    assert identities.backfill() == 2
    assert identities.backfill() == 0
    original, = identities.current()
    assert original["hostname"] == "current"

    inventory.mark_removed("current")
    assert identities.current() == []
    assert identities.record_rebuild(original["host_id"], 1) is None
    inventory.restore_host("current")
    inventory.save_host(host("current", "192.0.2.3"))
    changed, = identities.current()
    assert changed["host_id"] == original["host_id"]
    assert changed["current_incarnation"] == 1
    assert identities.record_rebuild(original["host_id"], 1) == 2
    assert identities.record_rebuild(original["host_id"], 1) is None
    assert [record["incarnation"] for record in identities.history(original["host_id"])] == [1, 2]


def test_pending_publication_recovers_identity_after_failed_backfill(monkeypatch, tmp_path):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "host-identity.db"))
    inventory = InventoryRepository()
    filename = tmp_path / "hosts.yml"
    filename.write_text("all:\n  children:\n    fixture:\n      hosts: {}\n")
    publication = InventoryPublication(filename, inventory)
    new_host = host("current", "192.0.2.1")

    def fail_backfill(self):
        raise RuntimeError("identity write failed")

    with monkeypatch.context() as patch:
        patch.setattr(HostIdentityRepository, "backfill", fail_backfill)
        with publication.locked(), publication.stage() as (writer, original):
            writer.filename.write_text(
                "all:\n  children:\n    fixture:\n      hosts:\n"
                "        current:\n          ansible_host: 192.0.2.1\n"
            )
            with pytest.raises(RuntimeError, match="identity write failed"):
                publication.publish(writer, original, "save_host", new_host)

    assert publication.journal.exists()
    assert inventory.find_host("current")["hostname"] == "current"
    with publication.locked():
        current, = HostIdentityRepository(inventory).current()
        assert current["hostname"] == "current"
    assert not publication.journal.exists()
    assert HostIdentityRepository(inventory).backfill() == 0
