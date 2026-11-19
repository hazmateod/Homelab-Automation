from types import SimpleNamespace

import pytest

from himp.services import reports
from himp.database.host_identity import HostIdentityRepository


@pytest.fixture
def report_host(tmp_path, monkeypatch):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "reports.db"))
    path = tmp_path / "hosts.yml"
    path.write_text("all: {}\n")
    monkeypatch.setattr(reports.config, "inventory", str(path))
    repository = reports.InventoryRepository()
    repository.save_host({
        "hostname": "fixture", "group": "managed", "ip": "192.0.2.2",
        "user": "fixture", "become": False,
    })
    inventory = {"_meta": {"hostvars": {"fixture": {"ansible_host": "192.0.2.2"}}}}
    monkeypatch.setattr(
        reports.HostMaintenanceEligibility, "read_inventory", lambda snapshot: inventory
    )
    return path, repository, inventory


@pytest.mark.parametrize("change", [None, "retired", "replaced", "source", "ambiguous"])
def test_report_retry_dispatches_only_the_verified_original_host(
    monkeypatch, report_host, change,
):
    path, repository, inventory = report_host
    calls = []

    def runner(playbook, limit, *, timeout, inventory_path):
        assert inventory_path != str(path)
        calls.append(limit)
        return SimpleNamespace(success=False, elapsed=1.0)

    monkeypatch.setattr(reports, "run_playbook", runner)
    service = reports.ReportService()
    first = service.generate("fixture")
    plan_id = first["target_plan_id"]
    if change == "retired":
        repository.mark_removed("fixture")
    elif change == "replaced":
        inventory["_meta"]["hostvars"]["fixture"]["ansible_user"] = "replacement"
    elif change == "source":
        path.write_text("all:\n  hosts: {}\n")
    elif change == "ambiguous":
        inventory["fixture"] = {"hosts": ["different-host"]}

    if change is None:
        retried = service.generate("fixture", expected_target_plan_id=plan_id)
        assert retried["target_plan_id"] != plan_id
        assert calls == ["fixture", "fixture"]
    else:
        with pytest.raises(reports.ReportTargetChangedError):
            service.generate("fixture", expected_target_plan_id=plan_id)
        assert calls == ["fixture"]


def test_verified_rebuild_blocks_retry_and_new_report_uses_new_incarnation(
    monkeypatch, report_host,
):
    _, repository, inventory = report_host
    inventory["_meta"]["hostvars"]["fixture"]["ansible_user"] = "fixture"
    identities = HostIdentityRepository(repository)
    identities.backfill()
    host_id = identities.current()[0]["host_id"]
    bindings = []

    def runner(playbook, limit, *, timeout, inventory_path, extra_vars):
        bindings.append(extra_vars["himp_host_bindings"][limit])
        return SimpleNamespace(success=True, elapsed=1.0)

    monkeypatch.setattr(reports, "run_playbook", runner)
    service = reports.ReportService()
    first = service.generate("fixture")
    assert identities.record_rebuild(host_id, 1) == 2
    with pytest.raises(reports.ReportTargetChangedError):
        service.generate("fixture", expected_target_plan_id=first["target_plan_id"])
    service.generate("fixture")
    assert [(binding["host_id"], binding["incarnation"]) for binding in bindings] == [
        (host_id, 1), (host_id, 2),
    ]
