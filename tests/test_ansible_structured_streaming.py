"""Phase 17.1 structured Ansible streaming integration tests."""

import json
import subprocess
import sys
from datetime import datetime, timezone

import pytest

from himp.lib import ansible


def install_fake_ansible(monkeypatch, code):
    original_popen = subprocess.Popen
    captured = {}

    def fake_popen(cmd, **kwargs):
        assert cmd[0] == "ansible-playbook"
        captured["environment"] = kwargs.get("env", {})

        return original_popen(
            [sys.executable, "-u", "-c", code],
            **kwargs,
        )

    monkeypatch.setattr(ansible.subprocess, "Popen", fake_popen)
    return captured


def test_structured_event_delivery(monkeypatch):
    payload = {
        "event": "task_ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": "synthetic-host",
        "task": "Synthetic task",
        "changed": False,
    }

    code = (
        "print('TASK [Synthetic task]',flush=True);"
        f"print('HIMP_EVENT:{json.dumps(payload)}',flush=True);"
        "print('PLAY RECAP',flush=True)"
    )

    captured = install_fake_ansible(monkeypatch, code)
    events = []
    console = []

    result = ansible.run_playbook_streaming(
        "synthetic.yml",
        timeout=5,
        structured_events=True,
        on_event=events.append,
        on_output=console.append,
    )

    assert result.success
    assert events == [payload]
    assert console == [
        "TASK [Synthetic task]",
        "PLAY RECAP",
    ]
    assert "ANSIBLE_CALLBACK_PLUGINS" in captured["environment"]
    assert captured["environment"]["ANSIBLE_CALLBACKS_ENABLED"] == (
        "himp_events"
    )


def test_malformed_event_fails_closed(monkeypatch):
    install_fake_ansible(
        monkeypatch,
        "print('HIMP_EVENT:{invalid-json}',flush=True)",
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid HIMP structured event",
    ):
        ansible.run_playbook_streaming(
            "synthetic.yml",
            timeout=5,
            structured_events=True,
            on_event=lambda event: None,
        )


def test_non_object_event_rejected(monkeypatch):
    install_fake_ansible(
        monkeypatch,
        "print('HIMP_EVENT:[]',flush=True)",
    )

    with pytest.raises(
        RuntimeError,
        match="HIMP event must be a JSON object",
    ):
        ansible.run_playbook_streaming(
            "synthetic.yml",
            timeout=5,
            structured_events=True,
            on_event=lambda event: None,
        )


def test_missing_event_type_rejected(monkeypatch):
    install_fake_ansible(
        monkeypatch,
        'print(\'HIMP_EVENT:{"host":"synthetic"}\',flush=True)',
    )

    with pytest.raises(
        RuntimeError,
        match="HIMP event missing event type",
    ):
        ansible.run_playbook_streaming(
            "synthetic.yml",
            timeout=5,
            structured_events=True,
            on_event=lambda event: None,
        )


def test_unexpected_fields_never_reach_callback(monkeypatch):
    payload = {
        "event": "task_ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": "synthetic-host",
        "task": "Synthetic task",
        "changed": False,
        "password": "synthetic-secret",
    }

    code = f"print('HIMP_EVENT:{json.dumps(payload)}',flush=True)"

    install_fake_ansible(monkeypatch, code)

    received = []

    with pytest.raises(
        RuntimeError,
        match="Rejected HIMP structured event",
    ):
        ansible.run_playbook_streaming(
            "synthetic.yml",
            timeout=5,
            structured_events=True,
            on_event=received.append,
        )

    assert received == []


def test_error_text_removed_before_callback(monkeypatch):
    payload = {
        "event": "failed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": "synthetic-host",
        "task": "Synthetic task",
        "changed": False,
        "error": "password=synthetic-secret",
    }

    code = f"print('HIMP_EVENT:{json.dumps(payload)}',flush=True)"

    install_fake_ansible(monkeypatch, code)

    received = []

    result = ansible.run_playbook_streaming(
        "synthetic.yml",
        timeout=5,
        structured_events=True,
        on_event=received.append,
    )

    assert result.success
    assert len(received) == 1
    assert received[0]["event"] == "failed"
    assert "error" not in received[0]
    assert "synthetic-secret" not in str(received)


def test_oversized_event_never_reaches_callback(monkeypatch):
    payload = {
        "event": "task_ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": "synthetic-host",
        "task": "X" * 20000,
        "changed": False,
    }

    code = f"print('HIMP_EVENT:{json.dumps(payload)}',flush=True)"

    install_fake_ansible(monkeypatch, code)

    received = []

    with pytest.raises(
        RuntimeError,
        match="HIMP event exceeds size limit",
    ):
        ansible.run_playbook_streaming(
            "synthetic.yml",
            timeout=5,
            structured_events=True,
            on_event=received.append,
        )

    assert received == []
