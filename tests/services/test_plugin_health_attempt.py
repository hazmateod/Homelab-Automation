import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from himp.sdk import health
from himp.services.health import HealthService
from himp.health.repository import HealthRepository
from himp.services.health_cards import HealthCardsService


@pytest.mark.parametrize("outcome", ["timeout", "failed", "missing", "malformed", "stale", "fresh", "superseded"])
def test_health_history_only_records_the_current_successful_attempt(monkeypatch, tmp_path, outcome):
    runner = health.PluginHealthRunner()
    runner.loader = SimpleNamespace(find=lambda name: SimpleNamespace(
        id=name, inventory_group=name,
    ))
    runner.REPORT_DIR = tmp_path
    identity = {"host_id": "resolver-id", "incarnation": 1}
    identities = Mock(
        return_value=SimpleNamespace(
            execution_bindings=lambda: {"resolver": {**identity, "ip": "192.0.2.1", "user": "test"}},
            current=lambda: [{"hostname": "resolver", "group_name": "technitium",
                              "host_id": "resolver-id", "current_incarnation": 1,
                              "endpoint_review_required": False}],
            report_bindings=lambda: {"resolver": identity},
        ),
    )
    monkeypatch.setattr(health, "HostIdentityRepository", identities)
    monkeypatch.setattr("himp.health.repository.HostIdentityRepository", identities)
    monkeypatch.setattr(
        "himp.database.host_automation_policies.HostAutomationPolicyRepository",
        Mock(return_value=SimpleNamespace(disabled_hosts=lambda: [])),
    )
    artifact = tmp_path / "technitium.json"
    artifact.write_text(json.dumps({
        "attempt_id": "old", "plugin": "technitium",
        "hosts": [{"hostname": "resolver", "host_identity": identity, "health": {"status": "PASS", "earned": 10, "possible": 10}}],
    }))

    def run(command, *, check, timeout, env):
        policy = next(json.loads(arg) for arg in command
                      if arg.startswith('{"ansible_host_key_checking"'))
        assert policy["ansible_ssh_host_key_checking"] is True
        assert policy["himp_require_technitium_ssh"] is True
        assert "StrictHostKeyChecking=yes" in policy["ansible_ssh_args"]
        assert env["LC_ALL"] == "C"
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(command, timeout)
        staged = next(json.loads(arg)["himp_health_output"] for arg in command
                      if arg.startswith('{"himp_health_output"'))
        from pathlib import Path
        staged = Path(staged)
        if outcome == "malformed":
            staged.write_text("{")
        if outcome == "stale":
            staged.write_bytes(artifact.read_bytes())
        if outcome in {"fresh", "superseded"}:
            argument = next(arg for arg in command if arg.startswith("himp_health_attempt_id="))
            document = json.loads(artifact.read_text())
            document["attempt_id"] = argument.split("=", 1)[1]
            staged.write_text(json.dumps(document))
        return SimpleNamespace(returncode=2 if outcome == "failed" else 0)

    monkeypatch.setattr(health.subprocess, "run", run)

    def read_report(name):
        document = json.loads(artifact.read_text())
        if outcome == "superseded":
            document["attempt_id"] = "concurrent-attempt"
        return SimpleNamespace(metadata=SimpleNamespace(data=document))

    service = HealthService()
    service.runner = runner
    service.repository = SimpleNamespace(plugin=Mock(side_effect=read_report))
    service.history = Mock()

    result = service.plugin("technitium")

    assert result.success is (outcome in {"fresh", "superseded"})
    assert result.return_code == {"timeout": 124, "failed": 2, "stale": 1, "missing": 1, "malformed": 1}.get(outcome, 0)
    assert bool(result.artifacts) is result.success
    assert service.history.record.call_count == int(outcome == "fresh")
    if not result.success:
        service.repository.plugin.assert_not_called()


    repository = HealthRepository()
    repository.REPORT_DIR = tmp_path
    service.repository = repository
    cards = HealthCardsService()
    cards.repository = repository
    summary, = service.summary().plugins
    card, = cards.all()
    expected_status = "PASS" if result.success else "UNKNOWN"
    assert summary.status == card["status"] == expected_status
    assert repository.plugin("technitium").summary.status == "PASS"
    assert summary.details["evidence_freshness"] == ("current" if result.success else "stale")
    assert summary.details["latest_attempt"]["attempt_id"] == result.health_attempt_id
    assert summary.details["latest_attempt"]["failure_category"] == {
        "timeout": "timeout", "failed": "execution_failed", "missing": "artifact_missing",
        "malformed": "artifact_invalid", "stale": "artifact_invalid",
    }.get(outcome)


def test_older_attempt_cannot_publish_after_newer_attempt(tmp_path):
    from himp.health.attempts import HealthAttempts

    attempts = HealthAttempts(tmp_path)
    old = tmp_path / "old.json"
    old.write_text("old")
    destination = tmp_path / "technitium.json"
    attempts.start("technitium", "older")
    attempts.start("technitium", "newer")
    attempts.finish("technitium", "newer", "timeout")

    assert attempts.finish("technitium", "older", None, old, destination) == "superseded"
    assert not destination.exists()
    assert attempts.all()["technitium"]["failure_category"] == "timeout"


def test_failed_publication_retains_previous_observation(tmp_path, monkeypatch):
    from pathlib import Path
    from himp.health.attempts import HealthAttempts

    attempts = HealthAttempts(tmp_path)
    destination = tmp_path / "technitium.json"
    destination.write_text("previous")
    staged = tmp_path / "staged.json"
    staged.write_text("new")
    attempts.start("technitium", "current")

    def blocked_replace(self, target):
        raise PermissionError("private path")

    monkeypatch.setattr(Path, "replace", blocked_replace)
    assert attempts.finish("technitium", "current", None, staged, destination) == "publication_failed"
    assert destination.read_text() == "previous"
    attempt = attempts.all()["technitium"]
    assert attempt["status"] == "failed"
    assert attempt["failure_category"] == "publication_failed"


def test_fleet_score_keeps_missing_unverified_retired_and_disabled_targets(tmp_path):
    from himp.health.parser import HealthArtifactParser
    from himp.health.technitium_fleet import project_fleet

    def member(name):
        return {"hostname": name, "group_name": "technitium", "host_id": name,
                "current_incarnation": 2, "endpoint_review_required": False}

    def observation(name, incarnation=2):
        return {"hostname": name, "host_identity": {"host_id": name, "incarnation": incarnation},
                "health": {"status": "PASS", "earned": 10, "possible": 10}}

    path = tmp_path / "technitium.json"
    path.write_text(json.dumps({"plugin": "technitium", "hosts": [
        observation("healthy"), observation("retired"), observation("disabled"),
        observation("replaced", 1), observation("outside"),
        observation("ambiguous"), observation("ambiguous"),
    ]}))
    report = HealthArtifactParser().parse(path)
    projected = project_fleet(
        report, [member(name) for name in ("healthy", "missing", "disabled", "replaced", "ambiguous")],
        {"disabled"}, "current", {"retired": None},
    )
    assert projected.summary.score == 10
    assert projected.summary.possible == 70
    assert projected.metadata.data["fleet_membership"] == {
        "healthy": 1, "unknown": 1, "unverified": 3, "retired": 1, "disabled": 1,
    }
    assert [host.hostname for host in projected.hosts if host.passed] == ["healthy"]
    assert report.summary.score == 70


@pytest.mark.parametrize("entrypoint", ["workflow", "scheduler"])
def test_health_dispatch_keeps_server_selected_fleet(entrypoint, monkeypatch, tmp_path):
    from pathlib import Path
    from himp.commands import scheduler_run
    from himp.services.automation import AutomationService
    from himp.services.workflow_execution import WorkflowExecutionService

    runner = health.PluginHealthRunner()
    runner.loader = SimpleNamespace(plugins=lambda: [SimpleNamespace(
        id="technitium", inventory_group="technitium", supports_health=lambda: True,
    )])
    runner.loader.find = lambda name: runner.loader.plugins()[0]
    runner.REPORT_DIR = tmp_path
    bindings = {
        name: {"host_id": f"{name}-id", "incarnation": 1, "ip": "192.0.2.1", "user": "test"}
        for name in ("resolver", "disabled", "unrelated")
    }
    monkeypatch.setattr(health, "HostIdentityRepository", lambda: SimpleNamespace(
        execution_bindings=lambda: bindings,
        current=lambda: [{"hostname": name, "group_name": group} for name, group in (
            ("resolver", "technitium"), ("disabled", "technitium"), ("unrelated", "pbs"),
        )],
    ))
    monkeypatch.setattr(
        "himp.database.host_automation_policies.HostAutomationPolicyRepository",
        lambda: SimpleNamespace(disabled_hosts=lambda: {"disabled"}),
    )
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        extra = [json.loads(arg) for arg in command if arg.startswith("{")]
        options = {key: value for entry in extra for key, value in entry.items()}
        attempt = next(arg.split("=", 1)[1] for arg in command if arg.startswith("himp_health_attempt_id="))
        Path(options["himp_health_output"]).write_text(json.dumps({
            "plugin": "technitium", "attempt_id": attempt, "hosts": [],
        }))
        assert "inventory_group=technitium" in command
        assert set(options["himp_host_bindings"]) == {"resolver", "disabled"}
        assert options["himp_health_disabled_hosts"] == ["disabled"]
        assert "--limit" not in command and not any("forged" in arg for arg in command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(health.subprocess, "run", run)
    service = HealthService()
    service.runner = runner
    automation = AutomationService()
    automation.health = service
    automation.lock_repository = Mock()
    automation.execution_repository = Mock()
    automation.execution_repository.save.return_value = 1
    monkeypatch.setattr(automation, "validate_execution_policy", lambda *args, **kwargs: {
        "timeout_seconds": 10, "retry_attempts": 1, "retry_delay_seconds": 0,
    })
    if entrypoint == "workflow":
        workflow = WorkflowExecutionService(
            workflow_service=SimpleNamespace(
                get_workflow=lambda _: {"id": 17},
                validate_workflow=lambda _: {"valid": True},
                repository=SimpleNamespace(
                    list_tasks=lambda _: [{"task_id": "health_check"}],
                    list_dependencies=lambda _: [],
                ),
            ),
            automation_service=automation,
            workflow_execution_repository=Mock(),
        )
        assert workflow.execute(17, limit="forged:pbs")["success"]
    else:
        monkeypatch.setattr(scheduler_run, "_run_vulnerability_ingest", lambda: None)
        monkeypatch.setattr(scheduler_run, "HIMP", lambda: SimpleNamespace(automation=automation))
        monkeypatch.setattr(scheduler_run, "SchedulerService", lambda: SimpleNamespace(
            due_tasks=lambda now: [{"task_id": "health_check"}], record_run=Mock(),
        ))
        monkeypatch.setattr(scheduler_run, "RemediationSchedulingService",
                            lambda: SimpleNamespace(due=lambda **kwargs: []))
        assert scheduler_run.run(SimpleNamespace(at=None)) == 0
    assert len(calls) == 1
