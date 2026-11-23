import json

import pytest

from himp.database.host_identity import HostIdentityRepository
from himp.database.inventory import InventoryRepository
from himp.health.repository import HealthRepository
from himp.models.ssh import SSHResult
from himp.services.host_health import HostHealthService
from himp.services.inventory_publication import InventoryPublication
from himp.services.reports import ReportService


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


def test_shadow_projections_match_verified_incarnations_and_keep_legacy_readable(
    monkeypatch, tmp_path,
):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "host-identity.db"))
    inventory = InventoryRepository()
    inventory.save_host(host("current", "192.0.2.1"))
    identities = HostIdentityRepository(inventory)
    identities.backfill()
    active, = identities.current()
    identity = {"host_id": active["host_id"], "incarnation": 1}

    reports = ReportService()
    reports.root = tmp_path / "reports"
    report_dir = reports.root / "json"
    report_dir.mkdir(parents=True)
    bound_report = {"host_identity": identity}
    (report_dir / "current.json").write_text(json.dumps(bound_report))
    (report_dir / "legacy.json").write_text("{}")
    health = HealthRepository()
    health.REPORT_DIR = tmp_path
    (tmp_path / "plugin.json").write_text(json.dumps({
        "plugin": "fixture",
        "hosts": [{"hostname": "current", "host_identity": identity}, {"hostname": "legacy"}],
    }))

    assert reports.current_host_reports() == {"current": bound_report}
    assert [(plugin, row.hostname) for plugin, row in health.current_hosts()] == [
        ("fixture", "current"),
    ]
    inventory_row = inventory.find_host("current")
    identities.rename(inventory_row["id"], "current", "renamed", "fixture-rename")
    assert reports.current_host_reports() == {"renamed": bound_report}
    assert [row.hostname for _, row in health.current_hosts()] == ["renamed"]

    inventory.mark_removed("renamed")
    assert reports.current_host_reports() == {}
    assert list(health.current_hosts()) == []
    inventory.restore_host("renamed")
    assert reports.current_host_reports() == {"renamed": bound_report}

    assert identities.record_rebuild(active["host_id"], 1) == 2
    assert reports.current_host_reports() == {}
    assert list(health.current_hosts()) == []
    assert len(reports.files()) == 2
    assert [row.hostname for row in health.plugin("plugin").hosts] == ["current", "legacy"]


def test_host_health_binds_only_when_incarnation_stays_stable(monkeypatch, tmp_path):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "host-identity.db"))
    service = HostHealthService()
    service.inventory.save_host(host("current", "192.0.2.1"))
    service.identities.backfill()
    host_id = service.identities.current()[0]["host_id"]

    def respond(*, timeout, **target):
        return SSHResult(**target)

    monkeypatch.setattr(service.ssh, "test", respond)
    bound = service.check_host("current").host_identity
    assert bound == {"host_id": host_id, "incarnation": 1}
    assert service.latest("current")["details"]["host_identity"] == bound

    def respond_after_rebuild(*, timeout, **target):
        assert service.identities.record_rebuild(host_id, 1) == 2
        return SSHResult(**target)

    monkeypatch.setattr(service.ssh, "test", respond_after_rebuild)
    assert service.check_host("current").host_identity is None
    assert "host_identity" not in service.latest("current")["details"]


def test_endpoint_change_hides_old_evidence_until_review(monkeypatch, tmp_path):
    import pytest

    from himp.services.inventory import InventoryService
    from himp.services.inventory_writer import InventoryFileWriter

    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "inventory.db"))
    service = InventoryService()
    service.writer = InventoryFileWriter(tmp_path / "hosts.yml")
    service.repository.save_host(host("fixture", "192.0.2.1"))
    identities = HostIdentityRepository(service.repository)
    identities.backfill()
    host_id = identities.current()[0]["host_id"]
    service.repository.save_host(host("fixture", "192.0.2.2"))
    assert identities.current_hostnames() == {}
    assert identities.execution_bindings() == {}
    with pytest.raises(ValueError, match="Verify the current inventory"):
        service.record_verified_move("fixture", host_id, 1, endpoint=("192.0.2.1", "synthetic"))
    assert service.record_verified_move("fixture", host_id, 1, endpoint=("192.0.2.2", "synthetic")) == {
        "host_id": host_id, "incarnation": 1,
    }
    assert identities.current_hostnames() == {(host_id, 1): "fixture"}

    service.repository.save_host(host("fixture", "192.0.2.3"))
    assert service.record_verified_rebuild(
        "fixture", host_id, 1, endpoint=("192.0.2.3", "synthetic")
    ) == {"host_id": host_id, "incarnation": 2}
    assert identities.current_hostnames() == {(host_id, 2): "fixture"}


def test_health_projects_only_verified_incarnations_across_reused_container_ids():
    from himp.health.models import HostHealthResult
    from himp.health.repository import HealthRepository
    from types import SimpleNamespace

    current = {}
    rows = []
    for ctid in (600, 601, 800, 801):
        for scope in ("blackwatch", "standalone"):
            host_id = f"{scope}-identity-{ctid}"
            current[(host_id, 2)] = f"{scope}-renamed-{ctid}"
            rows.append(HostHealthResult(
                hostname=f"{scope}-old-{ctid}", results=[],
                host_identity={"host_id": host_id, "incarnation": 2},
            ))
            rows.append(HostHealthResult(
                hostname=f"{scope}-stale-{ctid}", results=[],
                host_identity={"host_id": host_id, "incarnation": 1},
            ))
    rows += [
        HostHealthResult(hostname="retired", results=[], host_identity={"host_id": "retired", "incarnation": 2}),
        HostHealthResult(hostname="unverified", results=[], host_identity={"ctid": 600}),
    ]
    repository = HealthRepository()
    repository.current_plugins = lambda: [SimpleNamespace(
        hosts=rows, summary=SimpleNamespace(plugin="technitium"),
    )]
    projected = list(repository.current_hosts(current))
    assert {host.hostname for _, host in projected} == set(current.values())
    assert len(projected) == 8
