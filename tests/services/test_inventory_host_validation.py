import subprocess

import pytest

from himp.config import config
from himp.database.host_automation_policies import HostAutomationPolicyRepository
from himp.database.host_identity import HostIdentityRepository
from himp.services.inventory import InventoryService


from himp.services.inventory_writer import InventoryFileWriter


def make_service():
    return InventoryService.__new__(InventoryService)


@pytest.fixture
def inventory_service(tmp_path, monkeypatch):
    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "inventory.db"))
    service = InventoryService()
    inventory = tmp_path / "hosts.yml"
    inventory.write_text(
        "all:\n  children:\n    infrastructure:\n      hosts:\n"
        "        existing:\n          ansible_host: 192.0.2.1\n"
    )
    service.writer = InventoryFileWriter(inventory)
    service.repository.save_host({
        "hostname": "existing", "group": "infrastructure",
        "ip": "192.0.2.1", "user": "operator", "become": False,
    })
    return service


def test_validate_inventory_host_accepts_matching_inventory_and_ping(
    monkeypatch,
):
    service = make_service()

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)

        if command[0] == "ansible-inventory":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"ansible_host": "10.10.37.57"}',
                stderr="",
            )

        return subprocess.CompletedProcess(
            command,
            0,
            stdout="himpdb01.server.arpa | SUCCESS => {\"ping\": \"pong\"}",
            stderr="",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    result = service._validate_inventory_host(
        "himpdb01.server.arpa",
        "10.10.37.57",
    )

    assert result["ansible_host"] == "10.10.37.57"

    assert calls[0] == [
        "ansible-inventory",
        "-i",
        config.inventory,
        "--host",
        "himpdb01.server.arpa",
    ]

    assert "--json" not in calls[0]

    assert calls[1][0] == "ansible"
    assert calls[1][3] == "himpdb01.server.arpa"


def test_validate_rename_rejects_a_changed_ssh_user_before_connecting(monkeypatch):
    def resolve(command, **kwargs):
        assert command[0] == "ansible-inventory"
        return subprocess.CompletedProcess(
            command, 0, stdout='{"ansible_host":"192.0.2.1","ansible_user":"different"}',
        )

    monkeypatch.setattr("himp.services.inventory.subprocess.run", resolve)
    with pytest.raises(ValueError, match="Ansible inventory user changed"):
        make_service()._validate_inventory_host(
            "fixture", "192.0.2.1", expected_user="operator"
        )


def test_validate_inventory_host_rejects_unresolved_host(
    monkeypatch,
):
    service = make_service()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="Could not match supplied host pattern",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    with pytest.raises(
        ValueError,
        match="Ansible inventory validation failed",
    ):
        service._validate_inventory_host(
            "himpdb01.server.arpa",
            "10.10.37.57",
        )


def test_validate_inventory_host_rejects_wrong_ip(
    monkeypatch,
):
    service = make_service()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ansible_host": "10.10.37.99"}',
            stderr="",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    with pytest.raises(
        ValueError,
        match="Ansible inventory IP mismatch",
    ):
        service._validate_inventory_host(
            "himpdb01.server.arpa",
            "10.10.37.57",
        )


def test_validate_inventory_host_rejects_failed_ping(
    monkeypatch,
):
    service = make_service()

    def fake_run(command, **kwargs):
        if command[0] == "ansible-inventory":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"ansible_host": "10.10.37.57"}',
                stderr="",
            )

        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="UNREACHABLE",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    with pytest.raises(
        ValueError,
        match="Ansible SSH validation failed",
    ):
        service._validate_inventory_host(
            "himpdb01.server.arpa",
            "10.10.37.57",
        )


@pytest.mark.parametrize(("operation", "hostname"), [
    ("add_host", "new"), ("update_host", "existing"),
])
def test_rejected_candidate_never_changes_runtime_inventory(
    inventory_service, monkeypatch, operation, hostname,
):
    service = inventory_service
    original = service.writer.filename.read_bytes()

    def reject_candidate(**arguments):
        assert arguments["inventory_path"] != service.writer.filename
        assert "192.0.2.99" in arguments["inventory_path"].read_text()
        assert service.writer.filename.read_bytes() == original
        raise ValueError("validation failed")

    monkeypatch.setattr(service, "_validate_inventory_host", reject_candidate)
    with pytest.raises(ValueError, match="validation failed"):
        getattr(service, operation)(hostname, "infrastructure", "192.0.2.99", "operator")

    assert service.writer.filename.read_bytes() == original
    assert service.find_host("existing")["ip"] == "192.0.2.1"
    assert service.find_host("new") is None


@pytest.mark.parametrize(("operation", "hostname"), [
    ("add_host", "new"), ("update_host", "existing"),
])
def test_accepted_candidate_is_published(inventory_service, monkeypatch, operation, hostname):
    service = inventory_service
    monkeypatch.setattr(service, "_validate_inventory_host", lambda **kwargs: None)

    host = getattr(service, operation)(hostname, "infrastructure", "192.0.2.99", "operator")

    assert host["ip"] == "192.0.2.99"
    assert "192.0.2.99" in service.writer.filename.read_text()
    assert not service._publication().journal.exists()


def test_recovery_replays_database_operation(inventory_service, monkeypatch):
    service = inventory_service
    mark_removed = service.repository.mark_removed

    def fail_write(hostname):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(service.repository, "mark_removed", fail_write)
    with pytest.raises(RuntimeError, match="database unavailable"):
        service.remove_host("existing")

    assert service._publication().journal.exists()
    assert service.find_host("existing") is not None
    monkeypatch.setattr(service.repository, "mark_removed", mark_removed)
    with service._publication().locked():
        assert service.find_host("existing") is None
    assert not service._publication().journal.exists()


def test_external_edit_is_preserved(inventory_service, monkeypatch):
    service = inventory_service
    external = "all: {}\n"

    def edit_during_validation(**arguments):
        service.writer.filename.write_text(external)

    monkeypatch.setattr(service, "_validate_inventory_host", edit_during_validation)
    with pytest.raises(RuntimeError, match="changed while the edit"):
        service.add_host("new", "infrastructure", "192.0.2.99", "operator")

    assert service.writer.filename.read_text() == external
    assert service.find_host("new") is None
    assert not service._publication().journal.exists()


def test_remove_host_clears_all_memberships_and_syncs(inventory_service, monkeypatch):
    service = inventory_service
    path = service.writer.filename
    path.write_text(path.read_text() + "    second:\n      hosts:\n        existing:\n          ansible_host: 192.0.2.1\n")
    monkeypatch.setattr(config, "inventory", str(path))

    removed = service.remove_host("existing")

    assert not removed["active"]
    assert "existing:" not in path.read_text()
    assert service.sync()["synced"] == 0
    service.restore_host("existing")
    assert service.sync()["synced"] == 1


def test_remove_rejects_unsupported_nested_membership(inventory_service):
    service = inventory_service
    path = service.writer.filename
    original = path.read_text() + (
        "    parent:\n      children:\n        nested:\n"
        "          hosts:\n            existing:\n"
    )
    path.write_text(original)

    with pytest.raises(ValueError, match="unsupported membership"):
        service.remove_host("existing")

    assert path.read_text() == original
    assert service.find_host("existing") is not None


def test_rename_recovers_after_database_commit_and_preserves_policy(
    inventory_service, monkeypatch,
):
    service = inventory_service
    path = service.writer.filename
    path.write_text(path.read_text() + "    second:\n      hosts:\n        existing:\n")
    policies = HostAutomationPolicyRepository(service.repository.database)
    policies.set_policy("existing", False, "protected", "operator")
    identities = HostIdentityRepository(service.repository)
    identities.backfill()
    original, = identities.current()
    monkeypatch.setattr(service, "_validate_inventory_host", lambda **kwargs: None)
    rename = HostIdentityRepository.rename

    def interrupt_after_commit(self, *args):
        rename(self, *args)
        raise RuntimeError("interrupted after rename commit")

    with monkeypatch.context() as patch:
        patch.setattr(HostIdentityRepository, "rename", interrupt_after_commit)
        with pytest.raises(RuntimeError, match="interrupted after rename commit"):
            service.rename_host("existing", "new-name")

    assert service._publication().journal.exists()
    with service._publication().locked():
        renamed, = identities.current()
        assert renamed["host_id"] == original["host_id"]
        assert renamed["current_incarnation"] == original["current_incarnation"]
        assert [(row["old_hostname"], row["new_hostname"]) for row in
                identities.aliases(original["host_id"])] == [("existing", "new-name")]
        assert policies.disabled_hosts() == {"new-name"}
        assert path.read_text().count("new-name:") == 2
    assert not service._publication().journal.exists()


def test_verified_rebuild_requires_the_current_host_identity(inventory_service):
    service = inventory_service
    identities = HostIdentityRepository(service.repository)
    identities.backfill()
    host_id = identities.current()[0]["host_id"]

    with pytest.raises(ValueError, match="incarnation has changed"):
        service.record_verified_rebuild("existing", "other-host", 1)
    assert service.record_verified_rebuild("existing", host_id, 1) == {
        "host_id": host_id, "incarnation": 2,
    }
    with pytest.raises(ValueError, match="incarnation has changed"):
        service.record_verified_rebuild("existing", host_id, 1)


def test_onboarding_keeps_failed_verification_pending_until_facts_succeed(
    inventory_service, monkeypatch,
):
    import json
    from pathlib import Path

    failures = [True, False]
    calls = []

    def run(command, **kwargs):
        calls.append(command[0])
        if command[0] == "ansible-inventory":
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
                "ansible_host": "192.0.2.2", "ansible_user": "himp-automation",
                "ansible_become": True,
            }))
        assert command[3:] == [
            "all", "--become", "-m", "ansible.builtin.setup",
            "-a", "filter=ansible_distribution",
        ]
        candidate = json.loads(Path(command[2]).read_text())
        assert list(candidate["all"]["hosts"]) == ["new-host"]
        assert kwargs["timeout"] == 30
        if failures.pop(0):
            return subprocess.CompletedProcess(command, 2, stdout="Missing sudo password", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("himp.services.inventory.subprocess.run", run)
    settings = ("new-host", "infrastructure", "192.0.2.2", "himp-automation", True)
    inventory_service.add_host(*settings, readiness="pending")
    assert calls == ["ansible-inventory"]
    assert inventory_service.maintenance_readiness()["new-host"]["readiness_pending"]

    with pytest.raises(ValueError, match="Missing sudo password"):
        inventory_service.update_host(*settings, readiness="verify")
    assert inventory_service.maintenance_readiness()["new-host"]["readiness_pending"]

    inventory_service.update_host(*settings, readiness="verify")
    assert "new-host" not in inventory_service.maintenance_readiness()
