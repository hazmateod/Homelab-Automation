import json

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

import himp.api.workflows as workflows_api


class FakeWorkflowService:
    def __init__(self):
        self.workflows = [
            {
                "id": 1,
                "name": "Infrastructure Refresh",
                "description": "Test workflow",
                "enabled": 1,
            }
        ]

    def list_workflows(self):
        return self.workflows

    def create_workflow(self, name, description, enabled):
        return {
            "id": 2,
            "name": name,
            "description": description,
            "enabled": int(enabled),
        }

    def get_workflow(self, workflow_id):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        return self.workflows[0]

    def update_workflow(
        self,
        workflow_id,
        name,
        description,
        enabled,
    ):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        return {
            "id": workflow_id,
            "name": name,
            "description": description,
            "enabled": int(enabled),
        }

    def delete_workflow(self, workflow_id):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

    def add_task(
        self,
        workflow_id,
        task_id,
        position,
    ):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        if task_id == "missing":
            raise ValueError(
                "Unknown automation task: missing"
            )

        if task_id == "invalid":
            raise workflows_api.WorkflowValidationError(
                "Task already exists."
            )

        return {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "position": position,
        }

    def remove_task(
        self,
        workflow_id,
        task_id,
    ):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        if task_id == "missing":
            raise workflows_api.WorkflowTaskNotFoundError(
                "Workflow task does not exist."
            )

        return {
            "workflow_id": workflow_id,
            "task_id": task_id,
        }

    def add_dependency(
        self,
        workflow_id,
        task_id,
        depends_on_task_id,
    ):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        if task_id == "missing":
            raise workflows_api.WorkflowTaskNotFoundError(
                "Workflow task does not exist."
            )

        if task_id == "cycle":
            raise workflows_api.WorkflowDependencyCycleError(
                "Dependency would create a cycle."
            )

        if task_id == "invalid":
            raise workflows_api.WorkflowValidationError(
                "Dependency already exists."
            )

        return {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "depends_on_task_id": depends_on_task_id,
        }

    def remove_dependency(
        self,
        workflow_id,
        task_id,
        dependency_task_id,
    ):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        if task_id == "missing":
            raise workflows_api.WorkflowDependencyNotFoundError(
                "Workflow dependency does not exist."
            )

        return {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "depends_on_task_id": dependency_task_id,
        }

    def validate_workflow(self, workflow_id):
        if workflow_id != 1:
            raise workflows_api.WorkflowNotFoundError(
                "Workflow does not exist."
            )

        return {
            "workflow_id": workflow_id,
            "valid": True,
            "errors": [],
            "task_count": 2,
            "dependency_count": 1,
        }


@pytest.fixture
def service(monkeypatch):
    fake = FakeWorkflowService()
    monkeypatch.setattr(
        workflows_api,
        "workflow_service",
        fake,
    )
    return fake


def body(response):
    return json.loads(
        response.body.decode("utf-8")
    )


def test_list_workflows(service):
    response = workflows_api.list_workflows()

    assert response.status_code == 200
    assert body(response) == service.workflows


def test_create_workflow(service):
    request = workflows_api.WorkflowCreateRequest(
        name="New Workflow",
        description="Description",
        enabled=True,
    )

    response = workflows_api.create_workflow(request)

    assert response.status_code == 201
    assert body(response) == {
        "id": 2,
        "name": "New Workflow",
        "description": "Description",
        "enabled": 1,
    }


def test_create_workflow_validation_error(service):
    service.create_workflow = lambda **kwargs: (
        (_ for _ in ()).throw(
            workflows_api.WorkflowValidationError(
                "Workflow already exists."
            )
        )
    )

    request = workflows_api.WorkflowCreateRequest(
        name="Duplicate",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.create_workflow(request)

    assert captured.value.status_code == 400
    assert captured.value.detail == "Workflow already exists."


def test_get_workflow(service):
    response = workflows_api.get_workflow(1)

    assert response.status_code == 200
    assert body(response)["id"] == 1


def test_get_workflow_not_found(service):
    with pytest.raises(HTTPException) as captured:
        workflows_api.get_workflow(999)

    assert captured.value.status_code == 404
    assert captured.value.detail == "Workflow does not exist."


def test_update_workflow(service):
    request = workflows_api.WorkflowUpdateRequest(
        name="Updated",
        description="Updated description",
        enabled=False,
    )

    response = workflows_api.update_workflow(
        1,
        request,
    )

    assert response.status_code == 200
    assert body(response)["name"] == "Updated"
    assert body(response)["enabled"] == 0


def test_update_workflow_not_found(service):
    request = workflows_api.WorkflowUpdateRequest(
        name="Updated",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.update_workflow(
            999,
            request,
        )

    assert captured.value.status_code == 404


def test_update_workflow_validation_error(service):
    service.update_workflow = lambda *args, **kwargs: (
        (_ for _ in ()).throw(
            workflows_api.WorkflowValidationError(
                "Workflow already exists."
            )
        )
    )

    request = workflows_api.WorkflowUpdateRequest(
        name="Duplicate",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.update_workflow(
            1,
            request,
        )

    assert captured.value.status_code == 400


def test_delete_workflow(service):
    response = workflows_api.delete_workflow(1)

    assert response == {
        "message": "Workflow deleted successfully.",
    }


def test_delete_workflow_not_found(service):
    with pytest.raises(HTTPException) as captured:
        workflows_api.delete_workflow(999)

    assert captured.value.status_code == 404


def test_add_workflow_task(service):
    request = workflows_api.WorkflowTaskRequest(
        task_id="inventory_refresh",
        position=1,
    )

    response = workflows_api.add_workflow_task(
        1,
        request,
    )

    assert response.status_code == 201
    assert body(response)["task"]["task_id"] == "inventory_refresh"


def test_add_workflow_task_unknown_automation_task(service):
    request = workflows_api.WorkflowTaskRequest(
        task_id="missing",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.add_workflow_task(
            1,
            request,
        )

    assert captured.value.status_code == 400
    assert "Unknown automation task" in captured.value.detail


def test_add_workflow_task_validation_error(service):
    request = workflows_api.WorkflowTaskRequest(
        task_id="invalid",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.add_workflow_task(
            1,
            request,
        )

    assert captured.value.status_code == 400


def test_add_workflow_task_workflow_not_found(service):
    request = workflows_api.WorkflowTaskRequest(
        task_id="inventory_refresh",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.add_workflow_task(
            999,
            request,
        )

    assert captured.value.status_code == 404


def test_remove_workflow_task(service):
    response = workflows_api.remove_workflow_task(
        1,
        "inventory_refresh",
    )

    assert response.status_code == 200
    assert body(response)["task"]["task_id"] == "inventory_refresh"


def test_remove_workflow_task_not_found(service):
    with pytest.raises(HTTPException) as captured:
        workflows_api.remove_workflow_task(
            999,
            "inventory_refresh",
        )

    assert captured.value.status_code == 404


def test_remove_workflow_task_missing_task(service):
    with pytest.raises(HTTPException) as captured:
        workflows_api.remove_workflow_task(
            1,
            "missing",
        )

    assert captured.value.status_code == 404


def test_add_workflow_dependency(service):
    request = workflows_api.WorkflowDependencyRequest(
        task_id="generate_reports",
        depends_on_task_id="inventory_refresh",
    )

    response = workflows_api.add_workflow_dependency(
        1,
        request,
    )

    assert response.status_code == 201
    assert body(response)["dependency"]["task_id"] == (
        "generate_reports"
    )


def test_add_workflow_dependency_cycle(service):
    request = workflows_api.WorkflowDependencyRequest(
        task_id="cycle",
        depends_on_task_id="inventory_refresh",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.add_workflow_dependency(
            1,
            request,
        )

    assert captured.value.status_code == 400
    assert "cycle" in captured.value.detail


def test_add_workflow_dependency_validation_error(service):
    request = workflows_api.WorkflowDependencyRequest(
        task_id="invalid",
        depends_on_task_id="inventory_refresh",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.add_workflow_dependency(
            1,
            request,
        )

    assert captured.value.status_code == 400


def test_add_workflow_dependency_missing_task(service):
    request = workflows_api.WorkflowDependencyRequest(
        task_id="missing",
        depends_on_task_id="inventory_refresh",
    )

    with pytest.raises(HTTPException) as captured:
        workflows_api.add_workflow_dependency(
            1,
            request,
        )

    assert captured.value.status_code == 404


def test_remove_workflow_dependency(service):
    response = workflows_api.remove_workflow_dependency(
        1,
        "generate_reports",
        "inventory_refresh",
    )

    assert response.status_code == 200
    assert body(response)["dependency"][
        "depends_on_task_id"
    ] == "inventory_refresh"


def test_remove_workflow_dependency_not_found(service):
    with pytest.raises(HTTPException) as captured:
        workflows_api.remove_workflow_dependency(
            999,
            "generate_reports",
            "inventory_refresh",
        )

    assert captured.value.status_code == 404


def test_remove_workflow_dependency_missing_dependency(service):
    with pytest.raises(HTTPException) as captured:
        workflows_api.remove_workflow_dependency(
            1,
            "missing",
            "inventory_refresh",
        )

    assert captured.value.status_code == 404


def test_validate_workflow(service):
    response = workflows_api.validate_workflow(1)

    assert response.status_code == 200
    assert body(response)["valid"] is True
    assert body(response)["task_count"] == 2
    assert body(response)["dependency_count"] == 1


def test_validate_workflow_not_found(service):
    with pytest.raises(HTTPException) as captured:
        workflows_api.validate_workflow(999)

    assert captured.value.status_code == 404

def test_workflow_routes_require_session():
    from fastapi.testclient import TestClient

    from himp.api import server

    with TestClient(server.app) as client:
        response = client.get("/api/workflows")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
