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
    monkeypatch.setattr(health, "HostIdentityRepository", Mock(
        return_value=SimpleNamespace(execution_bindings=lambda: {}),
    ))
    monkeypatch.setattr(
        "himp.database.host_automation_policies.HostAutomationPolicyRepository",
        Mock(return_value=SimpleNamespace(disabled_hosts=lambda: [])),
    )
    artifact = tmp_path / "technitium.json"
    artifact.write_text(json.dumps({
        "attempt_id": "old", "plugin": "technitium",
        "hosts": [{"hostname": "resolver", "health": {"status": "PASS", "earned": 10, "possible": 10}}],
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
