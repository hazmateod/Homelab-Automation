import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from himp.sdk import health
from himp.services.health import HealthService


@pytest.mark.parametrize("outcome", ["timeout", "failed", "stale", "fresh", "superseded"])
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
    artifact.write_text(json.dumps({"attempt_id": "old"}))

    def run(command, *, check, timeout):
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(command, timeout)
        if outcome in {"fresh", "superseded"}:
            argument = next(arg for arg in command if arg.startswith("himp_health_attempt_id="))
            artifact.write_text(json.dumps({"attempt_id": argument.split("=", 1)[1]}))
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
    assert result.return_code == {"timeout": 124, "failed": 2, "stale": 1}.get(outcome, 0)
    assert bool(result.artifacts) is result.success
    assert service.history.record.call_count == int(outcome == "fresh")
    if not result.success:
        service.repository.plugin.assert_not_called()
