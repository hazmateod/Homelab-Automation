from datetime import datetime, timedelta, timezone

from himp.services.automation import AutomationService


class FakeLockRepository:
    def __init__(self, lock=None):
        self.lock = lock

    def get(self, task_id):
        return self.lock


def make_service(lock=None):
    service = AutomationService()
    service.lock_repository = FakeLockRepository(
        lock
    )
    return service


def test_idle_task_reports_not_running():
    service = make_service()

    result = service.active_execution_status(
        "scheduled_updates"
    )

    assert result == {
        "task_id": "scheduled_updates",
        "running": False,
        "started_at": None,
        "expires_at": None,
        "elapsed_seconds": None,
    }


def test_active_task_reports_running_state():
    now = datetime.now(timezone.utc)

    service = make_service(
        {
            "task_id": "scheduled_updates",
            "locked_at": (
                now - timedelta(seconds=30)
            ).replace(tzinfo=None),
            "expires_at": (
                now + timedelta(minutes=30)
            ).replace(tzinfo=None),
        }
    )

    result = service.active_execution_status(
        "scheduled_updates"
    )

    assert result["task_id"] == "scheduled_updates"
    assert result["running"] is True
    assert result["started_at"] is not None
    assert result["expires_at"] is not None
    assert result["elapsed_seconds"] >= 29


def test_expired_lock_reports_not_running():
    now = datetime.now(timezone.utc)

    service = make_service(
        {
            "task_id": "scheduled_updates",
            "locked_at": (
                now - timedelta(minutes=10)
            ).replace(tzinfo=None),
            "expires_at": (
                now - timedelta(minutes=5)
            ).replace(tzinfo=None),
        }
    )

    result = service.active_execution_status(
        "scheduled_updates"
    )

    assert result["running"] is False
    assert result["started_at"] is None
    assert result["expires_at"] is None
    assert result["elapsed_seconds"] is None


def test_unknown_task_status_is_rejected():
    service = make_service()

    try:
        service.active_execution_status(
            "does_not_exist"
        )
    except ValueError as error:
        assert "does not exist" in str(error)
    else:
        raise AssertionError(
            "Expected ValueError"
        )
