"""Phase 17.1 maintenance host-result integration tests."""

from types import SimpleNamespace

import pytest

from himp.services import update as update_module


class FakeEligibility:
    def __init__(self, eligible, excluded=None):
        self.eligible = eligible
        self.excluded = excluded or []

    def resolve(self, requested, mode, *, inventory_path):
        return {
            "eligible_hosts": self.eligible,
            "target_fingerprints": {host: "fixture" for host in self.eligible},
            "excluded_hosts": self.excluded,
        }


@pytest.mark.parametrize(
    "return_code,failed,expected_status",
    [
        (0, 0, "succeeded"),
        (2, 1, "failed"),
    ],
)
def test_maintenance_host_results(
    monkeypatch,
    return_code,
    failed,
    expected_status,
):
    calls = []

    def fake_run_playbook(playbook, limit, timeout=None, *, inventory_path=None):
        calls.append((playbook, limit, timeout))

        return SimpleNamespace(
            success=return_code == 0,
            return_code=return_code,
            elapsed=1.25,
            stdout=(
                "PLAY RECAP\n"
                "host1 : ok=3 changed=1 "
                "unreachable=0 "
                f"failed={failed} "
                "skipped=0 rescued=0 ignored=0"
            ),
            stderr="",
        )

    monkeypatch.setattr(
        update_module,
        "run_playbook",
        fake_run_playbook,
    )

    service = update_module.UpdateService(
        eligibility=FakeEligibility(
            eligible=["host1"],
            excluded=["host2"],
        )
    )

    result = service.update(
        "maintenance",
        timeout=30,
    )

    assert result["success"] is (return_code == 0)
    assert result["host_results"]["host1"]["status"] == (
        expected_status
    )
    assert result["eligible_hosts"] == ["host1"]
    assert result["excluded_hosts"] == ["host2"]
    assert result["return_code"] == return_code
    assert result["elapsed"] == 1.25
    assert len(calls) == 1
    assert calls[0][1:] == ("host1", 30)


def test_no_eligible_hosts_does_not_execute_ansible(
    monkeypatch,
):
    def unexpected_run(*args, **kwargs):
        raise AssertionError(
            "Ansible must not execute"
        )

    monkeypatch.setattr(
        update_module,
        "run_playbook",
        unexpected_run,
    )

    service = update_module.UpdateService(
        eligibility=FakeEligibility(
            eligible=[],
            excluded=["host2"],
        )
    )

    result = service.update("maintenance")

    assert result["success"] is True
    assert result["skipped"] is True
    assert result["host_results"] == {}
    assert result["excluded_hosts"] == ["host2"]


@pytest.mark.parametrize("change", ["newly eligible", "retired", "replaced"])
def test_changed_maintenance_plan_is_never_dispatched(monkeypatch, tmp_path, change):
    class ChangingEligibility(FakeEligibility):
        def resolve(self, requested, mode, *, inventory_path):
            results = super().resolve(requested, mode, inventory_path=inventory_path)
            results["eligible_hosts"] = list(self.eligible)
            if change == "replaced":
                results["target_fingerprints"]["host1"] = self.identity
            return results

    path = tmp_path / "hosts.yml"
    path.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(path))
    eligibility = ChangingEligibility(["host1"])
    eligibility.identity = "original"
    service = update_module.UpdateService(eligibility=eligibility)

    def mutate(eligible, excluded):
        if change == "newly eligible":
            eligibility.eligible.append("host2")
        elif change == "retired":
            eligibility.eligible.clear()
        else:
            eligibility.identity = "replacement"

    def unexpected_run(*args, **kwargs):
        pytest.fail("Ansible received a changed maintenance plan")

    monkeypatch.setattr(update_module, "run_playbook", unexpected_run)
    with pytest.raises(RuntimeError, match="target plan changed") as failure:
        service.update("maintenance", on_hosts_resolved=mutate)
    assert failure.value.target_plan_id


def test_inventory_revision_change_blocks_dispatch(monkeypatch, tmp_path):
    path = tmp_path / "hosts.yml"
    path.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(path))
    service = update_module.UpdateService(eligibility=FakeEligibility(["host1"]))

    def mutate(eligible, excluded):
        path.write_text("all:\n  hosts: {}\n")

    def unexpected_run(*args, **kwargs):
        pytest.fail("Ansible received an obsolete maintenance plan")

    monkeypatch.setattr(update_module, "run_playbook", unexpected_run)
    with pytest.raises(RuntimeError, match="target plan changed"):
        service.update("maintenance", on_hosts_resolved=mutate)


def test_failed_plan_persistence_blocks_dispatch(monkeypatch):
    class UnavailablePlanRepository:
        def save(self, plan):
            raise RuntimeError("plan storage unavailable")

    service = update_module.UpdateService(
        eligibility=FakeEligibility(["host1"]), plans=UnavailablePlanRepository()
    )

    def unexpected_run(*args, **kwargs):
        pytest.fail("Ansible received a maintenance plan without an audit record")

    monkeypatch.setattr(update_module, "run_playbook", unexpected_run)
    with pytest.raises(RuntimeError, match="plan storage unavailable"):
        service.update("maintenance")


def test_failed_middle_host_does_not_stop_later_host(monkeypatch, tmp_path):
    from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository

    inventory = tmp_path / "hosts.yml"
    inventory.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(inventory))
    hosts = ["fixture-first", "fixture-middle", "fixture-last"]
    calls = []

    def runner(playbook, host, **kwargs):
        calls.append(host)
        unreachable = int(host == hosts[1])
        return SimpleNamespace(
            success=not unreachable, return_code=4 if unreachable else 0,
            elapsed=0.1, stderr="",
            stdout=f"PLAY RECAP\n{host} : ok=1 unreachable={unreachable} failed=0",
        )

    monkeypatch.setattr(update_module, "run_playbook", runner)
    result = update_module.UpdateService(eligibility=FakeEligibility(hosts)).update("maintenance")
    assert calls == hosts
    assert result["status"] == "partial"
    assert not result["success"]
    persisted = MaintenanceOutcomeRepository().find(result["target_plan_id"])
    assert persisted == result["host_results"]
    assert [persisted[host]["status"] for host in hosts] == [
        "succeeded", "unreachable", "succeeded",
    ]


def test_dispatch_marker_survives_interruption_and_blocks_replay(monkeypatch, tmp_path):
    from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository

    inventory = tmp_path / "hosts.yml"
    inventory.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(inventory))
    service = update_module.UpdateService(eligibility=FakeEligibility(["fixture-crash"]))

    class WorkerExit(BaseException):
        pass

    def interrupt(*args, **kwargs):
        assert MaintenanceOutcomeRepository().requires_reconciliation("fixture-crash")
        raise WorkerExit()

    monkeypatch.setattr(update_module, "run_playbook", interrupt)
    with pytest.raises(WorkerExit):
        service.update("maintenance")

    def unexpected(*args, **kwargs):
        pytest.fail("Unverified mutation must not be replayed")

    monkeypatch.setattr(update_module, "run_playbook", unexpected)
    result = service.update("maintenance")
    assert result["host_results"]["fixture-crash"]["reason"] == "prior_mutation_unverified"
    assert not result["success"]


def test_real_ansible_isolates_unreachable_middle_host(monkeypatch, tmp_path):
    import shutil

    if shutil.which("ansible-playbook") is None:
        pytest.skip("ansible-core is required for the subprocess fixture")

    marker = tmp_path / "completed"
    playbook = tmp_path / "maintenance.yml"
    playbook.write_text(
        "- hosts: all\n"
        "  serial: 1\n"
        "  gather_facts: true\n"
        "  tasks:\n"
        "    - ansible.builtin.copy:\n"
        "        content: completed\n"
        f"        dest: {marker}\n"
        "      when: inventory_hostname == 'ansible-fixture-last'\n"
    )
    inventory = tmp_path / "hosts.yml"
    inventory.write_text(
        "all:\n"
        "  hosts:\n"
        "    ansible-fixture-first: {ansible_connection: local}\n"
        "    ansible-fixture-middle: {ansible_host: 127.0.0.1, ansible_port: 1}\n"
        "    ansible-fixture-last: {ansible_connection: local}\n"
    )
    hosts = ["ansible-fixture-first", "ansible-fixture-middle", "ansible-fixture-last"]
    monkeypatch.setattr(update_module.config, "inventory", str(inventory))
    monkeypatch.setattr(update_module.config, "maintenance_playbook", str(playbook))
    result = update_module.UpdateService(eligibility=FakeEligibility(hosts)).update(
        "maintenance", timeout=30,
    )
    assert marker.read_text() == "completed"
    assert result["status"] == "partial"
    assert result["host_results"][hosts[1]]["status"] == "unreachable"
