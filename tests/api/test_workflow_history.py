import json

import pytest
from fastapi import HTTPException

import himp.api.workflows as workflows_api


class FakeWorkflowHistoryService:
    def __init__(self):
        self.history_records = [
            {
                "workflow": {
                    "id": 1,
                    "name": "Infrastructure Refresh",
                    "description": "Test workflow",
                    "enabled": 1,
                },
                "workflow_execution_id": "run-002",
                "started_at": "2026-08-15T00:05:00+00:00",
                "completed_at": "2026-08-15T00:06:00+00:00",
                "success": True,
                "executions": [
                    {
                        "id": 20,
                        "task_id": "inventory_refresh",
                        "workflow_execution_id": "run-002",
                        "success": True,
                    },
                ],
            },
        ]

    def history(self, workflow_id, limit=50):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        return self.history_records[:limit]

    def get(
        self,
        workflow_id,
        workflow_execution_id,
    ):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        if workflow_execution_id != "run-002":
            return None

        return self.history_records[0]


@pytest.fixture
def history_service(monkeypatch):
    fake = FakeWorkflowHistoryService()

    monkeypatch.setattr(
        workflows_api,
        "workflow_history_service",
        fake,
    )

    return fake


def body(response):
    return json.loads(
        response.body.decode("utf-8")
    )


def test_workflow_history(history_service):
    response = workflows_api.workflow_history(
        1,
    )

    assert response.status_code == 200
    assert body(response) == (
        history_service.history_records
    )


def test_workflow_history_respects_limit(
    history_service,
):
    response = workflows_api.workflow_history(
        1,
        limit=10,
    )

    assert response.status_code == 200
    assert len(body(response)) == 1


def test_workflow_history_not_found(
    history_service,
):
    with pytest.raises(HTTPException) as captured:
        workflows_api.workflow_history(999)

    assert captured.value.status_code == 404
    assert captured.value.detail == (
        "Workflow does not exist."
    )


def test_workflow_history_run(
    history_service,
):
    response = workflows_api.workflow_history_run(
        1,
        "run-002",
    )

    assert response.status_code == 200
    assert body(response) == (
        history_service.history_records[0]
    )


def test_workflow_history_run_not_found(
    history_service,
):
    with pytest.raises(HTTPException) as captured:
        workflows_api.workflow_history_run(
            1,
            "missing-run",
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == (
        "Workflow execution does not exist."
    )


def test_workflow_history_run_workflow_not_found(
    history_service,
):
    with pytest.raises(HTTPException) as captured:
        workflows_api.workflow_history_run(
            999,
            "run-002",
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == (
        "Workflow does not exist."
    )
