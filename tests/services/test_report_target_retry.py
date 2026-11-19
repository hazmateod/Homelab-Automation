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


def test_unverified_report_exports_leave_verified_json_and_markdown_intact(tmp_path):
    import json
    from pathlib import Path
    import shutil

    from himp.lib.ansible import run_playbook

    if shutil.which("ansible-playbook") is None:
        pytest.skip("ansible-core is required for the report export fixture")
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    root = Path(__file__).resolve().parents[2]
    for filename in ("export_json.yml", "export_markdown.yml"):
        shutil.copyfile(root / "roles" / "report" / "tasks" / filename, playbooks / filename)
    playbook = playbooks / "render.yml"
    playbook.write_text(
        "- hosts: all\n"
        "  gather_facts: false\n"
        "  vars:\n"
        "    ansible_date_time: {date: '2026-01-01', time: '00:00:00'}\n"
        "    cmdb: {health: {disk: [], recommendations: []}}\n"
        "  tasks:\n"
        "    - ansible.builtin.include_tasks: export_json.yml\n"
        "    - ansible.builtin.include_tasks: export_markdown.yml\n"
    )
    inventory = tmp_path / "inventory.yml"
    inventory.write_text(
        "all:\n  hosts:\n    fixture:\n"
        "      ansible_connection: local\n      ansible_host: 192.0.2.1\n      ansible_user: fixture\n"
    )
    json_dir = tmp_path / "reports" / "json"
    markdown_dir = tmp_path / "reports" / "current" / "cmdb"
    identity = {"host_id": "00000000-0000-4000-8000-000000000001", "incarnation": 1}
    bound = run_playbook(str(playbook), "fixture", timeout=15, inventory_path=inventory, extra_vars={
        "himp_host_bindings": {"fixture": {**identity, "ip": "192.0.2.1", "user": "fixture"}},
    })
    assert bound.success, bound.stdout + bound.stderr
    verified_json = (json_dir / "fixture.json").read_bytes()
    verified_markdown = (markdown_dir / "fixture.md").read_bytes()
    assert json.loads(verified_json)["host_identity"] == identity
    for limit in ("fixture", None):
        unbound = run_playbook(str(playbook), limit, timeout=15, inventory_path=inventory)
        assert unbound.success, unbound.stdout + unbound.stderr
        assert (json_dir / "fixture.json").read_bytes() == verified_json
        assert (markdown_dir / "fixture.md").read_bytes() == verified_markdown
        assert "host_identity" not in json.loads((json_dir / "unverified" / "fixture.json").read_bytes())
        assert (markdown_dir / "unverified" / "fixture.md").is_file()

    replacement = {**identity, "incarnation": 2}
    regenerated = run_playbook(
        str(playbook), "fixture", timeout=15, inventory_path=inventory,
        extra_vars={"himp_host_bindings": {"fixture": {
            **replacement, "ip": "192.0.2.1", "user": "fixture",
        }}},
    )
    assert regenerated.success, regenerated.stdout + regenerated.stderr
    archive = tmp_path / "reports" / "history" / "cmdb" / identity["host_id"] / "1"
    assert (archive / "report.json").read_bytes() == verified_json
    assert json.loads((json_dir / "fixture.json").read_bytes())["host_identity"] == replacement
