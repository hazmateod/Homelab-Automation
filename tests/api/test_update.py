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


def test_non_admin_cannot_mutate_inventory_or_dispatch_maintenance(monkeypatch):
    from types import SimpleNamespace

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from himp.api import automation, dependencies, inventory, update, workflows

    monkeypatch.setattr(dependencies, "require_session", lambda request: SimpleNamespace(
        role="viewer", username="fixture",
    ))
    monkeypatch.setattr(dependencies, "log_security_event", lambda *args, **kwargs: None)
    app = FastAPI()
    for module in (automation, inventory, update, workflows):
        app.include_router(module.router)
    with TestClient(app) as client:
        for method, path in (
            ("POST", "/inventory/hosts"),
            ("POST", "/inventory/sync"),
            ("POST", "/update/host/fixture"),
            ("POST", "/update/group/fixture"),
            ("POST", "/automation/update_host/run"),
            ("POST", "/workflows/1/execute"),
        ):
            assert client.request(method, path).status_code == 403, path
