"""
Maintenance Window Service.

Provides administrator-defined blackout windows for scheduled
automation and scheduled remediation execution.

Manual operator execution is intentionally outside this boundary.
"""

from datetime import datetime, timezone

from himp.database.maintenance_windows import (
    MaintenanceWindowRepository,
)


class MaintenanceWindowService:
    """
    Maintenance-window validation and execution decisions.
    """

    def __init__(
        self,
        repository=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else MaintenanceWindowRepository()
        )

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    @staticmethod
    def _normalize_datetime(
        value,
        field_name,
    ):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(
                    value
                )
            except ValueError as exc:
                raise ValueError(
                    f"{field_name} must use ISO datetime format"
                ) from exc

        if not isinstance(
            value,
            datetime,
        ):
            raise ValueError(
                f"{field_name} must be a datetime"
            )

        if value.tzinfo is None:
            return value

        return value.astimezone(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    @staticmethod
    def _required_text(
        value,
        field_name,
    ):
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} is required"
            )

        return value.strip()

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
        name = self._required_text(
            name,
            "name",
        )

        reason = self._required_text(
            reason,
            "reason",
        )

        created_by = self._required_text(
            created_by,
            "created_by",
        )

        starts_at = self._normalize_datetime(
            starts_at,
            "starts_at",
        )

        ends_at = self._normalize_datetime(
            ends_at,
            "ends_at",
        )

        if ends_at <= starts_at:
            raise ValueError(
                "ends_at must be later than starts_at"
            )

        if task_id is not None:
            task_id = self._required_text(
                task_id,
                "task_id",
            )

        return self.repository.create(
            name=name,
            reason=reason,
            starts_at=starts_at,
            ends_at=ends_at,
            created_by=created_by,
            task_id=task_id,
            enabled=enabled,
        )

    def get(
        self,
        window_id,
    ):
        window = self.repository.find(
            window_id
        )

        if window is None:
            raise KeyError(
                "maintenance window does not exist: "
                f"{window_id}"
            )

        return window

    def list(
        self,
        limit=100,
        enabled=None,
    ):
        windows = self.repository.list(
            limit=limit,
            enabled=enabled,
        )

        return {
            "count": len(windows),
            "windows": windows,
        }

    def active(
        self,
        now=None,
        task_id=None,
    ):
        if now is not None:
            now = self._normalize_datetime(
                now,
                "now",
            )

        return self.repository.active(
            now=now,
            task_id=task_id,
        )

    def active_all(
        self,
        now=None,
    ):
        if now is not None:
            now = self._normalize_datetime(
                now,
                "now",
            )

        return self.repository.active_all(
            now=now,
        )

    def upcoming(
        self,
        now=None,
        limit=25,
    ):
        if now is not None:
            now = self._normalize_datetime(
                now,
                "now",
            )

        return self.repository.upcoming(
            now=now,
            limit=limit,
        )

    def blocking_window(
        self,
        task_id,
        now=None,
    ):
        windows = self.active(
            now=now,
            task_id=task_id,
        )

        if not windows:
            return None

        return windows[0]

    def blocked(
        self,
        task_id,
        now=None,
    ):
        return (
            self.blocking_window(
                task_id=task_id,
                now=now,
            )
            is not None
        )

    def set_enabled(
        self,
        window_id,
        enabled,
    ):
        self.get(
            window_id
        )

        return self.repository.set_enabled(
            window_id=window_id,
            enabled=enabled,
        )
