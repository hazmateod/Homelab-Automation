import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from himp.api import maintenance_windows


class FakeMaintenanceWindowService:
    def __init__(self):
        self.windows = [
            {
                "id": 1,
                "name": "Global Maintenance",
                "reason": "Infrastructure work",
                "task_id": None,
                "starts_at": "2026-08-24T01:00:00",
                "ends_at": "2026-08-24T02:00:00",
                "enabled": True,
                "created_by": "admin",
            }
        ]

        self.create_calls = []
        self.enabled_calls = []

    def list(self):
        return {
            "count": len(self.windows),
            "windows": self.windows,
        }

    def active_all(self):
        return self.windows

    def upcoming(self):
        return []

    def get(self, window_id):
        if window_id != 1:
            raise KeyError(
                f"maintenance window does not exist: {window_id}"
            )

        return self.windows[0]

    def create(self, **kwargs):
        self.create_calls.append(kwargs)

        return {
            **self.windows[0],
            **kwargs,
        }

    def set_enabled(
        self,
        window_id,
        enabled,
    ):
        if window_id != 1:
            raise KeyError(
                f"maintenance window does not exist: {window_id}"
            )

        self.enabled_calls.append(
            {
                "window_id": window_id,
                "enabled": enabled,
            }
        )

        return {
            **self.windows[0],
            "enabled": enabled,
        }


def test_summary_returns_windows_active_and_upcoming(
    monkeypatch,
):
    service = FakeMaintenanceWindowService()

    monkeypatch.setattr(
        maintenance_windows,
        "service",
        service,
    )

    response = asyncio.run(
        maintenance_windows.maintenance_window_summary()
    )

    assert response["count"] == 1
    assert response["windows"] == service.windows
    assert response["active"] == service.windows
    assert response["upcoming"] == []


def test_detail_returns_window(
    monkeypatch,
):
    service = FakeMaintenanceWindowService()

    monkeypatch.setattr(
        maintenance_windows,
        "service",
        service,
    )

    response = asyncio.run(
        maintenance_windows.maintenance_window_detail(
            1
        )
    )

    assert response["id"] == 1


def test_missing_window_returns_404(
    monkeypatch,
):
    monkeypatch.setattr(
        maintenance_windows,
        "service",
        FakeMaintenanceWindowService(),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        asyncio.run(
            maintenance_windows.maintenance_window_detail(
                999
            )
        )

    assert captured.value.status_code == 404


def test_admin_create_uses_authenticated_username(
    monkeypatch,
):
    service = FakeMaintenanceWindowService()

    monkeypatch.setattr(
        maintenance_windows,
        "service",
        service,
    )

    request = maintenance_windows.MaintenanceWindowCreate(
        name="Patch Window",
        reason="Patch infrastructure",
        starts_at="2026-08-24T01:00:00+00:00",
        ends_at="2026-08-24T02:00:00+00:00",
        task_id="scheduled_updates",
    )

    admin = SimpleNamespace(
        username="admin"
    )

    response = asyncio.run(
        maintenance_windows.create_maintenance_window(
            request=request,
            admin=admin,
        )
    )

    assert response["message"] == (
        "Maintenance window created successfully."
    )

    assert service.create_calls[0]["created_by"] == "admin"
    assert service.create_calls[0]["task_id"] == (
        "scheduled_updates"
    )


def test_enabled_update_delegates_to_service(
    monkeypatch,
):
    service = FakeMaintenanceWindowService()

    monkeypatch.setattr(
        maintenance_windows,
        "service",
        service,
    )

    response = asyncio.run(
        maintenance_windows.update_maintenance_window_enabled(
            window_id=1,
            request=(
                maintenance_windows.
                MaintenanceWindowEnabledUpdate(
                    enabled=False
                )
            ),
        )
    )

    assert response["window"]["enabled"] is False

    assert service.enabled_calls == [
        {
            "window_id": 1,
            "enabled": False,
        }
    ]


def test_maintenance_routes_require_session():
    from fastapi.testclient import TestClient
    from himp.api import server

    with TestClient(server.app) as client:
        response = client.get(
            "/api/maintenance-windows"
        )

    assert response.status_code == 401
