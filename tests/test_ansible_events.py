"""Phase 17.1 structured event validation tests."""

from datetime import datetime, timezone

import pytest

from himp.lib.ansible_events import validate_ansible_event


@pytest.fixture
def timestamp():
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def valid_event(timestamp):
    return {
        "event": "task_ok",
        "timestamp": timestamp,
        "host": "synthetic-host",
        "task": "Synthetic task",
        "changed": False,
    }


def test_valid_task_event(valid_event):
    assert validate_ansible_event(valid_event) == valid_event


def test_unexpected_field_rejected(valid_event):
    valid_event["password"] = "synthetic-secret"

    with pytest.raises(ValueError, match="Unexpected"):
        validate_ansible_event(valid_event)


def test_oversized_event_rejected(valid_event):
    valid_event["task"] = "X" * 20000

    with pytest.raises(ValueError, match="size limit"):
        validate_ansible_event(valid_event)


def test_unknown_event_rejected(valid_event):
    valid_event["event"] = "execute_command"

    with pytest.raises(ValueError, match="Unsupported"):
        validate_ansible_event(valid_event)


def test_missing_timestamp_rejected(valid_event):
    del valid_event["timestamp"]

    with pytest.raises(ValueError, match="timestamp"):
        validate_ansible_event(valid_event)


def test_naive_timestamp_rejected(valid_event):
    valid_event["timestamp"] = "2026-11-08T12:00:00"

    with pytest.raises(ValueError, match="timezone"):
        validate_ansible_event(valid_event)


def test_invalid_changed_flag_rejected(valid_event):
    valid_event["changed"] = "false"

    with pytest.raises(ValueError, match="changed"):
        validate_ansible_event(valid_event)


def test_error_text_excluded(timestamp):
    payload = {
        "event": "failed",
        "timestamp": timestamp,
        "host": "synthetic-host",
        "task": "Synthetic task",
        "changed": False,
        "error": "password=synthetic-secret",
    }

    result = validate_ansible_event(payload)

    assert "error" not in result
    assert "synthetic-secret" not in str(result)


def test_valid_host_summary(timestamp):
    payload = {
        "event": "playbook_finished",
        "timestamp": timestamp,
        "hosts": {
            "synthetic-host": {
                "ok": 3,
                "changed": 1,
                "failed": 0,
                "unreachable": 0,
                "skipped": 1,
            }
        },
    }

    result = validate_ansible_event(payload)

    assert result["hosts"]["synthetic-host"]["ok"] == 3


def test_invalid_host_counter_rejected(timestamp):
    payload = {
        "event": "playbook_finished",
        "timestamp": timestamp,
        "hosts": {
            "synthetic-host": {
                "ok": -1,
                "changed": 0,
                "failed": 0,
                "unreachable": 0,
                "skipped": 0,
            }
        },
    }

    with pytest.raises(ValueError, match="counter"):
        validate_ansible_event(payload)


def test_excessive_hosts_rejected(timestamp):
    payload = {
        "event": "playbook_finished",
        "timestamp": timestamp,
        "hosts": {
            f"host-{index}": {
                "ok": 1,
                "changed": 0,
                "failed": 0,
                "unreachable": 0,
                "skipped": 0,
            }
            for index in range(101)
        },
    }

    with pytest.raises(ValueError, match="host summary"):
        validate_ansible_event(payload)


def test_invalid_host_name_rejected(valid_event):
    valid_event["host"] = "bad\nhost"

    with pytest.raises(ValueError, match="name"):
        validate_ansible_event(valid_event)
