from himp.database.host_identity import HostIdentityRepository
from himp.database.inventory import InventoryRepository


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
