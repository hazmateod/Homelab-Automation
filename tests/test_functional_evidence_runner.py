from pathlib import Path
from unittest.mock import Mock, patch

from himp.models.plugin import Plugin
from himp.sdk.functional_evidence import (
    PluginFunctionalEvidenceRunner,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PLAYBOOK = (
    PROJECT_ROOT
    / "playbooks"
    / "run_functional_evidence.yml"
)


def plugin(
    supports=True,
):
    return Plugin(
        id="example",
        name="Example",
        version="1.0.0",
        description="Example plugin",
        inventory_group="example_group",
        supports={
            "functional_evidence": supports,
        },
        manifest=(
            PROJECT_ROOT
            / "plugins"
            / "example"
            / "plugin.yml"
        ),
    )


def test_freepbx_declares_functional_evidence_capability():
    from himp.plugins.loader import PluginLoader

    freepbx = PluginLoader().find("freepbx")

    assert freepbx is not None
    assert freepbx.supports_functional_evidence()
    assert freepbx.has_functional_evidence()
    assert freepbx.functional_evidence_ready()


def test_functional_evidence_playbook_is_separate_from_health():
    source = PLAYBOOK.read_text(
        encoding="utf-8"
    )

    assert (
        "tasks/functional_evidence.yml"
        in source
    )
    assert "tasks/health.yml" not in source
    assert "run_health.yml" not in source


def test_functional_evidence_playbook_writes_own_artifact():
    source = PLAYBOOK.read_text(
        encoding="utf-8"
    )

    assert (
        "reports/functional_evidence"
        in source
    )
    assert "reports/health" not in source


def test_missing_plugin_fails_without_ansible():
    runner = PluginFunctionalEvidenceRunner()

    runner.loader.find = Mock(
        return_value=None
    )

    with patch(
        "himp.sdk.functional_evidence.subprocess.run"
    ) as run:
        result = runner.collect(
            "missing"
        )

    assert result.success is False
    assert result.return_code == 1
    assert result.warning_count() == 1
    run.assert_not_called()


def test_not_ready_plugin_fails_without_ansible():
    runner = PluginFunctionalEvidenceRunner()

    item = plugin()

    runner.loader.find = Mock(
        return_value=item
    )

    with patch.object(
        item,
        "functional_evidence_ready",
        return_value=False,
    ):
        with patch(
            "himp.sdk.functional_evidence.subprocess.run"
        ) as run:
            result = runner.collect(
                "example"
            )

    assert result.success is False
    assert result.return_code == 1
    assert result.warning_count() == 1
    run.assert_not_called()


def test_runner_uses_functional_evidence_playbook():
    runner = PluginFunctionalEvidenceRunner()

    item = plugin()

    runner.loader.find = Mock(
        return_value=item
    )

    process = Mock()
    process.returncode = 0

    with patch.object(
        item,
        "functional_evidence_ready",
        return_value=True,
    ):
        with patch(
            "himp.sdk.functional_evidence.subprocess.run",
            return_value=process,
        ) as run:
            runner.collect(
                "example",
                timeout=30,
            )

    command = run.call_args.args[0]

    assert (
        "playbooks/run_functional_evidence.yml"
        in command
    )
    assert "plugin=example" in command
    assert (
        "inventory_group=example_group"
        in command
    )
    assert (
        "playbooks/run_health.yml"
        not in command
    )


def test_collect_all_selects_only_ready_plugins():
    runner = PluginFunctionalEvidenceRunner()

    ready = Mock()
    ready.id = "ready"
    ready.functional_evidence_ready.return_value = True

    not_ready = Mock()
    not_ready.id = "not-ready"
    not_ready.functional_evidence_ready.return_value = False

    runner.loader.plugins = Mock(
        return_value=[
            ready,
            not_ready,
        ]
    )

    runner.collect = Mock(
        return_value=Mock()
    )

    runner.collect_all()

    runner.collect.assert_called_once_with(
        "ready",
        timeout=None,
    )
