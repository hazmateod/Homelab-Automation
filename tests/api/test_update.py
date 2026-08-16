import asyncio

import pytest

from himp.api import update


class FakeInventory:
    def __init__(self, host=None):
        self.host = host

    def find_host(self, hostname):
        return self.host


class FakeAutomation:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def run(self, task_id, limit=None, confirmed=False):
        self.calls.append(
            {
                "task_id": task_id,
                "limit": limit,
                "confirmed": confirmed,
            }
        )

        return self.result


class FakeHIMP:
    def __init__(self, automation):
        self.automation = automation


def test_update_host_uses_automation_service(monkeypatch):
    automation = FakeAutomation(
        result={
            "id": 123,
            "task": "update_host",
            "success": True,
            "attempt": 1,
            "attempts": 1,
            "result": {
                "target": "update_host",
                "limit": "himpdb01.server.arpa",
                "success": True,
            },
        }
    )

    monkeypatch.setattr(
        update,
        "inventory",
        FakeInventory(
            host={
                "hostname": "himpdb01.server.arpa",
            }
        ),
    )

    monkeypatch.setattr(
        update,
        "himp",
        FakeHIMP(automation),
    )

    result = asyncio.run(
        update.update_host(
            "himpdb01.server.arpa"
        )
    )

    assert result == {
        "id": 123,
        "task": "update_host",
        "success": True,
        "attempt": 1,
        "attempts": 1,
        "result": {
            "target": "update_host",
            "limit": "himpdb01.server.arpa",
            "success": True,
        },
    }

    assert automation.calls == [
        {
            "task_id": "update_host",
            "limit": "himpdb01.server.arpa",
            "confirmed": True,
        }
    ]


def test_update_host_missing_inventory_host_returns_404(
    monkeypatch,
):
    monkeypatch.setattr(
        update,
        "inventory",
        FakeInventory(),
    )

    with pytest.raises(
        update.HTTPException
    ) as captured:
        asyncio.run(
            update.update_host(
                "missing.server.arpa"
            )
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == {
        "error": "Host not found",
        "hostname": "missing.server.arpa",
    }
