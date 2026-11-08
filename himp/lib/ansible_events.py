"""Strict validation of structured Ansible progress events."""

import json
from datetime import datetime

MAX_EVENT_BYTES = 16384
MAX_HOSTS = 100
MAX_NAME_LENGTH = 255

EVENT_FIELDS = {
    "play_started": {"play"},
    "task_started": {"task"},
    "task_ok": {"host", "task", "changed"},
    "failed": {"host", "task", "changed", "error"},
    "unreachable": {"host", "task", "changed", "error"},
    "skipped": {"host", "task", "changed"},
    "playbook_finished": {"hosts"},
}

COUNTERS = {
    "ok", "changed", "failed", "unreachable", "skipped"
}


def _name(value):
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_NAME_LENGTH
        or any(ord(char) < 32 for char in value)
    ):
        raise ValueError("Invalid Ansible event name")

    return value


def validate_ansible_event(payload):
    """Return an allowlisted, persistence-safe event."""

    if not isinstance(payload, dict):
        raise ValueError("Ansible event must be an object")

    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Invalid Ansible event encoding"
        ) from error

    if len(encoded) > MAX_EVENT_BYTES:
        raise ValueError("Ansible event exceeds size limit")

    event = payload.get("event")

    if event not in EVENT_FIELDS:
        raise ValueError("Unsupported Ansible event type")

    allowed = EVENT_FIELDS[event] | {"event", "timestamp"}

    if set(payload) - allowed:
        raise ValueError("Unexpected Ansible event fields")

    timestamp = payload.get("timestamp")

    if not isinstance(timestamp, str):
        raise ValueError("Missing Ansible event timestamp")

    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as error:
        raise ValueError("Invalid event timestamp") from error

    if parsed.tzinfo is None:
        raise ValueError("Event timestamp must include timezone")

    result = {
        "event": event,
        "timestamp": timestamp,
    }

    if event == "play_started":
        result["play"] = _name(payload.get("play"))

    elif event == "task_started":
        result["task"] = _name(payload.get("task"))

    elif event == "playbook_finished":
        hosts = payload.get("hosts")

        if not isinstance(hosts, dict) or len(hosts) > MAX_HOSTS:
            raise ValueError("Invalid host summary")

        result["hosts"] = {}

        for host, summary in hosts.items():
            host = _name(host)

            if not isinstance(summary, dict):
                raise ValueError("Invalid host counters")

            if set(summary) != COUNTERS:
                raise ValueError("Invalid host counter fields")

            counters = {}

            for key in COUNTERS:
                value = summary[key]

                if (
                    type(value) is not int
                    or value < 0
                    or value > 1000000
                ):
                    raise ValueError("Invalid host counter")

                counters[key] = value

            result["hosts"][host] = counters

    else:
        result["host"] = _name(payload.get("host"))
        result["task"] = _name(payload.get("task"))

        if type(payload.get("changed")) is not bool:
            raise ValueError("Invalid changed flag")

        result["changed"] = payload["changed"]

        # Deliberately discard error text. It may contain secrets.
        # Host status comes from the final Ansible recap.
        if event in {"failed", "unreachable"}:
            if "error" in payload and not isinstance(
                payload["error"], str
            ):
                raise ValueError("Invalid error field")

    return result
