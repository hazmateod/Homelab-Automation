import asyncio

import pytest

from himp.api import update


class FakeInventory:
    def __init__(self, groups=None):
        self.groups = groups or []

    def summary(self):
        class Statistics:
            group_counts = [
                type("Group", (), {"name": name})()
                for name in self.groups
            ]

        return type(
            "Summary",
            (),
            {"statistics": Statistics()},
        )()


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


def test_update_group_uses_automation_service(monkeypatch):
    automation = FakeAutomation(
        result={
            "id": 124,
            "task": "update_group",
            "success": True,
            "attempt": 1,
            "attempts": 1,
            "result": {
                "target": "update_group",
                "limit": "infrastructure",
                "success": True,
            },
        }
    )

    monkeypatch.setattr(
        update,
        "inventory",
        FakeInventory(
            groups=["infrastructure"]
        ),
    )

    monkeypatch.setattr(
        update,
        "himp",
        FakeHIMP(automation),
    )

    result = asyncio.run(
        update.update_group(
            "infrastructure"
        )
    )

    assert result == {
        "id": 124,
        "task": "update_group",
        "success": True,
        "attempt": 1,
        "attempts": 1,
        "result": {
            "target": "update_group",
            "limit": "infrastructure",
            "success": True,
        },
    }

    assert automation.calls == [
        {
            "task_id": "update_group",
            "limit": "infrastructure",
            "confirmed": True,
        }
    ]


def test_update_group_missing_group_returns_404(monkeypatch):
    monkeypatch.setattr(
        update,
        "inventory",
        FakeInventory(
            groups=["infrastructure"]
        ),
    )

    with pytest.raises(
        update.HTTPException
    ) as captured:
        asyncio.run(
            update.update_group(
                "does-not-exist"
            )
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == {
        "error": "Inventory group not found",
        "group": "does-not-exist",
    }
