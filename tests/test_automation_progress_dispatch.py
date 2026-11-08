"""Phase 17.1 maintenance progress dispatch integration tests."""

import pytest

from himp.services.automation import AutomationService


class FakeLifecycle:
    def __init__(self):
        self.calls = []

    def start_safely(self, eligible, excluded):
        self.calls.append(
            ("resolved", list(eligible), list(excluded))
        )

    def handle_event_safely(self, event):
        self.calls.append(("event", event))


class FakeUpdates:
    def __init__(self):
        self.calls = []

    def update(self, target, limit=None, timeout=None, **kwargs):
        self.calls.append((target, limit, timeout, kwargs))

        if "on_hosts_resolved" in kwargs:
            kwargs["on_hosts_resolved"](["host01"], [])

        if "on_event" in kwargs:
            kwargs["on_event"](
                {
                    "event": "synthetic",
                    "host": "host01",
                }
            )

        return {
            "target": target,
            "success": True,
        }


@pytest.mark.parametrize(
    "task_id,target,limit",
    [
        ("scheduled_updates", "maintenance", None),
        ("update_host", "update_host", "host01"),
        ("update_group", "update_group", "infrastructure"),
    ],
)
def test_maintenance_dispatch_forwards_progress_callbacks(
    task_id,
    target,
    limit,
):
    service = object.__new__(AutomationService)
    service.updates = FakeUpdates()

    lifecycle = FakeLifecycle()

    result = service._execute_task(
        task_id,
        limit=limit,
        timeout=60,
        progress_lifecycle=lifecycle,
    )

    assert result["success"] is True

    assert len(service.updates.calls) == 1

    called_target, called_limit, timeout, kwargs = (
        service.updates.calls[0]
    )

    assert called_target == target
    assert called_limit == limit
    assert timeout == 60

    assert callable(kwargs["on_hosts_resolved"])
    assert callable(kwargs["on_event"])

    assert lifecycle.calls == [
        ("resolved", ["host01"], []),
        (
            "event",
            {
                "event": "synthetic",
                "host": "host01",
            },
        ),
    ]


def test_legacy_dispatch_does_not_pass_progress_callbacks():
    service = object.__new__(AutomationService)
    service.updates = FakeUpdates()

    result = service._execute_task(
        "update_host",
        limit="host01",
        timeout=60,
    )

    assert result["success"] is True

    _, _, _, kwargs = service.updates.calls[0]

    assert kwargs == {}
