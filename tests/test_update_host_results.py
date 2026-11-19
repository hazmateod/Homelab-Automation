"""Phase 17.1 maintenance host-result integration tests."""

from types import SimpleNamespace

import pytest

from himp.services import update as update_module


@pytest.fixture(autouse=True)
def stub_dashboard(monkeypatch):
    monkeypatch.setattr(
        update_module.UpdateService,
        "_refresh_dashboard",
        staticmethod(lambda *args: {"status": "succeeded"}),
    )


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


def test_recovery_read_distinguishes_unknown_dispatch_from_unstarted(tmp_path, monkeypatch):
    from himp.database.automation_target_plans import AutomationTargetPlanRepository
    from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository

    inventory = tmp_path / "hosts.yml"
    inventory.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(inventory))
    plans = AutomationTargetPlanRepository()
    ids = []

    class TrackingPlans:
        def save(self, plan):
            plan_id = plans.save(plan)
            ids.append(plan_id)
            return plan_id

    class WorkerExit(BaseException):
        pass

    def interrupt(*args, **kwargs):
        raise WorkerExit()

    monkeypatch.setattr(update_module, "run_playbook", interrupt)
    service = update_module.UpdateService(
        eligibility=FakeEligibility(["fixture-unknown", "fixture-unstarted"]),
        plans=TrackingPlans(),
    )
    with pytest.raises(WorkerExit):
        service.update("maintenance")

    outcomes = MaintenanceOutcomeRepository()
    assert outcomes.read_plan_outcomes(ids[0]) == {
        "fixture-unknown": {"host": "fixture-unknown", "status": "interrupted",
                            "reason": "completion_unverified"},
        "fixture-unstarted": {"host": "fixture-unstarted", "status": "unstarted"},
    }
    legacy = plans.save({"task": "maintenance", "eligible_hosts": ["fixture-unknown"]})
    assert outcomes.read_plan_outcomes(legacy) is None


def test_reconcile_preserves_interruption_and_clears_only_selected_marker():
    from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository

    outcomes = MaintenanceOutcomeRepository()
    host = "fixture-reconcile"
    outcomes.start("fixture-plan-one", host)
    outcomes.start("fixture-plan-two", host)
    assert outcomes.reconcile("fixture-plan-one", host, "Verified package state locally")
    assert outcomes.requires_reconciliation(host)
    assert not outcomes.reconcile("fixture-plan-one", host, "Duplicate acknowledgement")
    assert outcomes.reconcile("fixture-plan-two", host, "Confirmed no remote process remained")
    assert not outcomes.requires_reconciliation(host)
    assert outcomes.find("fixture-plan-one")[host]["status"] == "interrupted"


@pytest.mark.parametrize("terminal", ["failed", "unreachable"])
def test_mutated_failure_requires_reconciliation_before_next_dispatch(monkeypatch, tmp_path, terminal):
    from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository
    from himp.services.inventory_publication import InventoryBusyError, inventory_admission

    inventory = tmp_path / "hosts.yml"
    inventory.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(inventory))
    hostname = f"fixture-mutated-{terminal}"
    calls = []

    def runner(playbook, host, **kwargs):
        calls.append(host)
        with pytest.raises(InventoryBusyError):
            with inventory_admission(inventory):
                pytest.fail("A concurrent inventory writer was admitted")
        return SimpleNamespace(
            success=False, return_code=2, elapsed=0.1, stderr="",
            stdout=f"PLAY RECAP\n{host} : ok=4 changed=1 {terminal}=1",
        )

    monkeypatch.setattr(update_module, "run_playbook", runner)
    service = update_module.UpdateService(eligibility=FakeEligibility([hostname]))
    first = service.update("maintenance")
    assert first["host_results"][hostname]["status"] == terminal
    assert service.update("maintenance")["host_results"][hostname]["reason"] == "prior_mutation_unverified"
    assert calls == [hostname]
    repository = MaintenanceOutcomeRepository()
    assert repository.reconcile(first["target_plan_id"], hostname, "Verified state")
    assert not repository.requires_reconciliation(hostname)


@pytest.mark.parametrize("streaming", [False, True])
def test_renamed_host_preserves_holds_and_dispatches_verified_report_binding(
    monkeypatch, tmp_path, streaming,
):
    from himp.database.host_identity import HostIdentityRepository
    from himp.database.inventory import InventoryRepository
    from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository

    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "inventory.db"))
    path = tmp_path / "hosts.yml"
    path.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(path))
    inventory = InventoryRepository()
    inventory.save_host({
        "hostname": "old", "group": "test", "ip": "192.0.2.1", "user": "fixture", "become": False,
    })
    identities = HostIdentityRepository(inventory)
    identities.backfill()
    host_id = identities.current()[0]["host_id"]
    outcomes = MaintenanceOutcomeRepository()
    outcomes.start("legacy-plan", "old")
    outcomes.start("bound-plan", "old", host_id=host_id)
    identities.rename(inventory.find_host("old")["id"], "old", "new", "fixture-op")
    calls = []

    def runner(playbook, host, **options):
        calls.append(options["extra_vars"]["himp_host_bindings"][host])
        return SimpleNamespace(
            success=True, return_code=0, elapsed=0.1, stderr="",
            stdout=f"PLAY RECAP\n{host} : ok=1 changed=0 unreachable=0 failed=0",
        )

    monkeypatch.setattr(update_module, "run_playbook_streaming" if streaming else "run_playbook", runner)
    service = update_module.UpdateService(eligibility=FakeEligibility(["new"]))
    kwargs = {"on_event": lambda event: None} if streaming else {}
    assert outcomes.reconcile("bound-plan", "old", "Fixture verified")
    assert service.update("maintenance", **kwargs)["host_results"]["new"]["reason"] == "prior_mutation_unverified"
    assert not calls
    assert outcomes.reconcile("legacy-plan", "old", "Fixture verified")
    result = service.update("maintenance", **kwargs)
    assert calls == [{"host_id": host_id, "incarnation": 1, "ip": "192.0.2.1", "user": "fixture"}]
    assert outcomes.find(result["target_plan_id"])["new"]["host_id"] == host_id


def test_ssh_user_mismatch_blocks_maintenance_before_report_changes(monkeypatch, tmp_path):
    from himp.database.inventory import InventoryRepository
    from himp.services.host_maintenance_eligibility import HostMaintenanceEligibility

    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "inventory.db"))
    inventory = tmp_path / "hosts.yml"
    inventory.write_text("all: {}\n")
    monkeypatch.setattr(update_module.config, "inventory", str(inventory))
    repository = InventoryRepository()
    repository.save_host({
        "hostname": "fixture", "group": "test", "ip": "192.0.2.1",
        "user": "approved", "become": False,
    })
    eligibility = HostMaintenanceEligibility(inventory_repository=repository)
    monkeypatch.setattr(eligibility, "read_inventory", lambda path: {
        "_meta": {"hostvars": {"fixture": {"ansible_host": "192.0.2.1", "ansible_user": "different"}}},
        "maintenance": {"hosts": ["fixture"]},
    })
    report = tmp_path / "fixture.json"
    report.write_text('{"host_identity":{"host_id":"verified","incarnation":1}}')

    def unexpected(*args, **kwargs):
        pytest.fail("Maintenance must not dispatch for a mismatched SSH user")

    monkeypatch.setattr(update_module, "run_playbook", unexpected)
    monkeypatch.setattr(update_module, "run_playbook_streaming", unexpected)
    service = update_module.UpdateService(eligibility=eligibility)
    with pytest.raises(ValueError, match="Maintenance SSH user differs"):
        service.update("maintenance")
    assert report.read_text() == '{"host_identity":{"host_id":"verified","incarnation":1}}'
