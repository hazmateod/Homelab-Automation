from datetime import datetime, timedelta, timezone

import pytest

from himp.services.maintenance_windows import (
    MaintenanceWindowService,
)


class FakeMaintenanceWindowRepository:
    def __init__(self):
        self.windows = []
        self.enabled_calls = []

    def create(
        self,
        name,
        reason,
        starts_at,
        ends_at,
        created_by,
        task_id=None,
        enabled=True,
    ):
        window = {
            "id": len(self.windows) + 1,
            "name": name,
            "reason": reason,
            "task_id": task_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "enabled": enabled,
            "created_by": created_by,
            "created_at": starts_at,
            "updated_at": starts_at,
        }

        self.windows.append(window)

        return window

    def find(self, window_id):
        for window in self.windows:
            if window["id"] == window_id:
                return window

        return None

    def list(
        self,
        limit=100,
        enabled=None,
    ):
        windows = list(self.windows)

        if enabled is not None:
            windows = [
                window
                for window in windows
                if window["enabled"] is enabled
            ]

        return windows[:limit]

    def active(
        self,
        now=None,
        task_id=None,
    ):
        now = now or datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        result = []

        for window in self.windows:
            if not window["enabled"]:
                continue

            if not (
                window["starts_at"] <= now < window["ends_at"]
            ):
                continue

            if window["task_id"] is None:
                result.append(window)
                continue

            if (
                task_id is not None
                and window["task_id"] == task_id
            ):
                result.append(window)

        return result

    def active_all(
        self,
        now=None,
    ):
        now = now or datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        return [
            window
            for window in self.windows
            if (
                window["enabled"]
                and window["starts_at"]
                <= now
                < window["ends_at"]
            )
        ]

    def upcoming(
        self,
        now=None,
        limit=25,
    ):
        now = now or datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        return [
            window
            for window in self.windows
            if (
                window["enabled"]
                and window["starts_at"] > now
            )
        ][:limit]

    def set_enabled(
        self,
        window_id,
        enabled,
    ):
        window = self.find(window_id)

        if window is None:
            raise KeyError(
                f"maintenance window does not exist: {window_id}"
            )

        window["enabled"] = enabled

        self.enabled_calls.append(
            {
                "window_id": window_id,
                "enabled": enabled,
            }
        )

        return window


def utc_naive(
    year,
    month,
    day,
    hour,
    minute=0,
):
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        tzinfo=timezone.utc,
    ).replace(
        tzinfo=None
    )


def test_create_maintenance_window_normalizes_and_persists():
    repository = FakeMaintenanceWindowRepository()

    service = MaintenanceWindowService(
        repository=repository
    )

    result = service.create(
        name="Database Maintenance",
        reason="Apply PostgreSQL updates",
        starts_at="2026-08-24T01:00:00+00:00",
        ends_at="2026-08-24T02:00:00+00:00",
        created_by="admin",
        task_id="scheduled_updates",
    )

    assert result["name"] == "Database Maintenance"
    assert result["reason"] == "Apply PostgreSQL updates"
    assert result["task_id"] == "scheduled_updates"

    assert result["starts_at"] == utc_naive(
        2026,
        8,
        24,
        1,
    )

    assert result["ends_at"] == utc_naive(
        2026,
        8,
        24,
        2,
    )


def test_create_rejects_invalid_window_order():
    service = MaintenanceWindowService(
        repository=FakeMaintenanceWindowRepository()
    )

    with pytest.raises(
        ValueError,
        match="ends_at must be later than starts_at",
    ):
        service.create(
            name="Bad Window",
            reason="Invalid range",
            starts_at="2026-08-24T02:00:00+00:00",
            ends_at="2026-08-24T01:00:00+00:00",
            created_by="admin",
        )


def test_global_window_blocks_any_task():
    repository = FakeMaintenanceWindowRepository()
    service = MaintenanceWindowService(
        repository=repository
    )

    now = utc_naive(
        2026,
        8,
        24,
        1,
    )

    service.create(
        name="Global Maintenance",
        reason="Infrastructure work",
        starts_at=now - timedelta(minutes=30),
        ends_at=now + timedelta(minutes=30),
        created_by="admin",
    )

    assert service.blocked(
        "health_check",
        now=now,
    )

    assert service.blocked(
        "scheduled_updates",
        now=now,
    )


def test_task_window_only_blocks_matching_task():
    repository = FakeMaintenanceWindowRepository()
    service = MaintenanceWindowService(
        repository=repository
    )

    now = utc_naive(
        2026,
        8,
        24,
        1,
    )

    service.create(
        name="Updates Only",
        reason="Patch infrastructure",
        starts_at=now - timedelta(minutes=30),
        ends_at=now + timedelta(minutes=30),
        created_by="admin",
        task_id="scheduled_updates",
    )

    assert service.blocked(
        "scheduled_updates",
        now=now,
    )

    assert not service.blocked(
        "health_check",
        now=now,
    )


def test_active_all_returns_global_and_task_specific_windows():
    repository = FakeMaintenanceWindowRepository()
    service = MaintenanceWindowService(
        repository=repository
    )

    now = utc_naive(
        2026,
        8,
        24,
        1,
    )

    service.create(
        name="Global",
        reason="Global maintenance",
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(minutes=10),
        created_by="admin",
    )

    service.create(
        name="Health",
        reason="Health maintenance",
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(minutes=10),
        created_by="admin",
        task_id="health_check",
    )

    active = service.active_all(
        now=now
    )

    assert [
        window["name"]
        for window in active
    ] == [
        "Global",
        "Health",
    ]


def test_disabled_window_does_not_block():
    repository = FakeMaintenanceWindowRepository()
    service = MaintenanceWindowService(
        repository=repository
    )

    now = utc_naive(
        2026,
        8,
        24,
        1,
    )

    window = service.create(
        name="Disabled",
        reason="Not currently enforced",
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(minutes=10),
        created_by="admin",
    )

    service.set_enabled(
        window["id"],
        False,
    )

    assert not service.blocked(
        "health_check",
        now=now,
    )
