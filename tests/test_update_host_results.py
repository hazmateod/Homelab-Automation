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
