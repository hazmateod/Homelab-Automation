from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from himp.api import remediation


class FakeSchedulingService:
    def __init__(self):
        self.schedule_calls = []
        self.list_calls = []
        self.get_calls = []
        self.cancel_calls = []

    def schedule(
        self,
        approval_id,
        scheduled_for,
        scheduled_by,
    ):
        self.schedule_calls.append(
            {
                "approval_id": approval_id,
                "scheduled_for": scheduled_for,
                "scheduled_by": scheduled_by,
            }
        )

        if approval_id == 404:
            raise KeyError(
                "approval does not exist"
            )

        if approval_id == 409:
            raise ValueError(
                "only an approved remediation can be scheduled"
            )

        return {
            "id": 1,
            "approval_id": approval_id,
            "status": "SCHEDULED",
        }

    def list(
        self,
        limit=100,
        status=None,
    ):
        self.list_calls.append(
            {
                "limit": limit,
                "status": status,
            }
        )

        if status == "INVALID":
            raise ValueError(
                "invalid remediation schedule status"
            )

        return {
            "count": 0,
            "summary": {
                "total": 0,
                "scheduled": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
            },
            "schedules": [],
        }

    def get(self, schedule_id):
        self.get_calls.append(
            schedule_id
        )

        if schedule_id == 404:
            raise KeyError(
                "remediation schedule does not exist"
            )

        return {
            "id": schedule_id,
            "status": "SCHEDULED",
        }

    def cancel(
        self,
        schedule_id,
        cancelled_by,
        cancellation_note=None,
    ):
        self.cancel_calls.append(
            {
                "schedule_id": schedule_id,
                "cancelled_by": cancelled_by,
                "cancellation_note": cancellation_note,
            }
        )

        if schedule_id == 404:
            raise KeyError(
                "remediation schedule does not exist"
            )

        if schedule_id == 409:
            raise ValueError(
                "only a scheduled remediation can be cancelled"
            )

        return {
            "id": schedule_id,
            "status": "CANCELLED",
        }


@pytest.fixture
def fake_service():
    original = (
        remediation.remediation_scheduling_service
    )

    fake = FakeSchedulingService()

    remediation.remediation_scheduling_service = (
        fake
    )

    yield fake

    remediation.remediation_scheduling_service = (
        original
    )


def admin():
    return SimpleNamespace(
        username="admin",
        role="admin",
    )


def test_create_schedule_records_admin_identity(
    fake_service,
):
    request = (
        remediation.RemediationScheduleCreateRequest(
            scheduled_for=datetime.fromisoformat(
                "2026-08-22T15:00:00+00:00"
            )
        )
    )

    result = remediation.create_remediation_schedule(
        approval_id=7,
        request=request,
        admin=admin(),
    )

    assert result["status"] == "SCHEDULED"

    assert fake_service.schedule_calls[0][
        "approval_id"
    ] == 7

    assert fake_service.schedule_calls[0][
        "scheduled_by"
    ] == "admin"


def test_create_missing_approval_returns_404(
    fake_service,
):
    request = (
        remediation.RemediationScheduleCreateRequest(
            scheduled_for=datetime.fromisoformat(
                "2026-08-22T15:00:00+00:00"
            )
        )
    )

    with pytest.raises(
        HTTPException
    ) as error:
        remediation.create_remediation_schedule(
            approval_id=404,
            request=request,
            admin=admin(),
        )

    assert error.value.status_code == 404


def test_create_invalid_schedule_returns_409(
    fake_service,
):
    request = (
        remediation.RemediationScheduleCreateRequest(
            scheduled_for=datetime.fromisoformat(
                "2026-08-22T15:00:00+00:00"
            )
        )
    )

    with pytest.raises(
        HTTPException
    ) as error:
        remediation.create_remediation_schedule(
            approval_id=409,
            request=request,
            admin=admin(),
        )

    assert error.value.status_code == 409


def test_list_schedule_queue_delegates(
    fake_service,
):
    result = remediation.remediation_schedule_queue(
        limit=25,
        status="SCHEDULED",
    )

    assert result["count"] == 0

    assert fake_service.list_calls == [
        {
            "limit": 25,
            "status": "SCHEDULED",
        }
    ]


def test_get_missing_schedule_returns_404(
    fake_service,
):
    with pytest.raises(
        HTTPException
    ) as error:
        remediation.remediation_schedule_detail(
            schedule_id=404
        )

    assert error.value.status_code == 404


def test_cancel_schedule_records_admin_identity(
    fake_service,
):
    request = (
        remediation.RemediationScheduleCancelRequest(
            note="Deferred.",
        )
    )

    result = remediation.cancel_remediation_schedule(
        schedule_id=8,
        request=request,
        admin=admin(),
    )

    assert result["status"] == "CANCELLED"

    assert fake_service.cancel_calls == [
        {
            "schedule_id": 8,
            "cancelled_by": "admin",
            "cancellation_note": "Deferred.",
        }
    ]


def test_schedule_routes_are_registered():
    from himp.api.server import app

    paths = app.openapi()["paths"]

    required = {
        "/api/remediation/schedules": {
            "get",
            "post",
        },
        (
            "/api/remediation/schedules/"
            "{schedule_id}"
        ): {
            "get",
        },
        (
            "/api/remediation/schedules/"
            "{schedule_id}/cancel"
        ): {
            "post",
        },
    }

    for path, methods in required.items():
        assert path in paths
        assert methods.issubset(
            set(paths[path])
        )
