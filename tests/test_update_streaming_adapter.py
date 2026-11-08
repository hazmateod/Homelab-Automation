"""Synthetic tests for opt-in maintenance streaming."""

from types import SimpleNamespace

import pytest

import himp.services.update as update_module
from himp.services.update import UpdateService


class FakeEligibility:
    def __init__(self, hosts):
        self.hosts = hosts

    def resolve(self, requested, mode):
        return {
            "eligible_hosts": self.hosts,
            "excluded_hosts": [],
        }


def fake_result():
    return SimpleNamespace(
        success=True,
        return_code=0,
        elapsed=0.25,
        stdout="",
        stderr="",
    )


def test_default_uses_existing_runner(monkeypatch):
    calls = []

    def legacy(playbook, limit, timeout=None):
        calls.append((playbook, limit, timeout))
        return fake_result()

    def unexpected(*args, **kwargs):
        pytest.fail("Streaming runner must not execute")

    monkeypatch.setattr(
        update_module, "run_playbook", legacy
    )
    monkeypatch.setattr(
        update_module, "run_playbook_streaming", unexpected
    )

    service = UpdateService(
        eligibility=FakeEligibility(["host01"])
    )

    result = service.update(
        "update_host",
        limit="host01",
        timeout=30,
    )

    assert result["success"] is True
    assert len(calls) == 1
    assert calls[0][1] == "host01"


def test_callback_activates_structured_streaming(monkeypatch):
    calls = []
    events = []

    def streaming(playbook, limit, **kwargs):
        calls.append((playbook, limit, kwargs))
        kwargs["on_event"]({"event": "synthetic"})
        return fake_result()

    def unexpected(*args, **kwargs):
        pytest.fail("Legacy runner must not execute")

    monkeypatch.setattr(
        update_module, "run_playbook_streaming", streaming
    )
    monkeypatch.setattr(
        update_module, "run_playbook", unexpected
    )

    service = UpdateService(
        eligibility=FakeEligibility(["host01"])
    )

    result = service.update(
        "update_host",
        limit="host01",
        timeout=30,
        on_event=events.append,
    )

    assert result["success"] is True
    assert events == [{"event": "synthetic"}]
    assert len(calls) == 1
    assert calls[0][1] == "host01"
    assert calls[0][2]["structured_events"] is True
    assert calls[0][2]["timeout"] == 30


def test_no_eligible_hosts_never_execute(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Ansible must not execute")

    monkeypatch.setattr(
        update_module, "run_playbook", unexpected
    )
    monkeypatch.setattr(
        update_module, "run_playbook_streaming", unexpected
    )

    service = UpdateService(
        eligibility=FakeEligibility([])
    )

    result = service.update(
        "update_host",
        limit="host01",
        on_event=lambda event: None,
    )

    assert result["success"] is True
    assert result["skipped"] is True
    assert result["eligible_hosts"] == []


def test_host_resolution_precedes_streaming(monkeypatch):
    order = []

    def streaming(playbook, limit, **kwargs):
        assert order == [
            ("resolved", ["host01"], []),
        ]
        order.append(("executed", limit))
        return fake_result()

    monkeypatch.setattr(
        update_module,
        "run_playbook_streaming",
        streaming,
    )

    service = UpdateService(
        eligibility=FakeEligibility(["host01"])
    )

    result = service.update(
        "update_host",
        limit="host01",
        on_event=lambda event: None,
        on_hosts_resolved=lambda eligible, excluded: (
            order.append(("resolved", eligible, excluded))
        ),
    )

    assert result["success"] is True
    assert order == [
        ("resolved", ["host01"], []),
        ("executed", "host01"),
    ]


def test_empty_eligibility_reports_hosts_without_execution(
    monkeypatch,
):
    resolved = []

    def unexpected(*args, **kwargs):
        pytest.fail("Ansible must not execute")

    monkeypatch.setattr(
        update_module,
        "run_playbook",
        unexpected,
    )
    monkeypatch.setattr(
        update_module,
        "run_playbook_streaming",
        unexpected,
    )

    service = UpdateService(
        eligibility=FakeEligibility([])
    )

    result = service.update(
        "update_host",
        limit="host01",
        on_event=lambda event: None,
        on_hosts_resolved=lambda eligible, excluded: (
            resolved.append((eligible, excluded))
        ),
    )

    assert resolved == [([], [])]
    assert result["skipped"] is True
    assert result["eligible_hosts"] == []
