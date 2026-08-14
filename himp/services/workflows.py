"""
Workflow definition service.
"""

from himp.database.workflows import WorkflowRepository
from himp.services.automation import AutomationService


class WorkflowNotFoundError(ValueError):
    """Raised when a workflow does not exist."""


class WorkflowTaskNotFoundError(ValueError):
    """Raised when a workflow task does not exist."""


class WorkflowDependencyNotFoundError(ValueError):
    """Raised when a workflow dependency does not exist."""


class WorkflowValidationError(ValueError):
    """Raised when a workflow definition is invalid."""


class WorkflowDependencyCycleError(WorkflowValidationError):
    """Raised when a workflow dependency would create a cycle."""


class WorkflowService:
    """
    Applies business rules to workflow definitions.

    Workflow persistence is delegated to WorkflowRepository.
    Automation task existence is delegated to AutomationService.
    """

    def __init__(
        self,
        repository=None,
        automation_service=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else WorkflowRepository()
        )

        self.automation_service = (
            automation_service
            if automation_service is not None
            else AutomationService()
        )

    # ------------------------------------------------------------------
    # Workflow operations
    # ------------------------------------------------------------------

    def create_workflow(
        self,
        name,
        description="",
        enabled=True,
    ):
        if not isinstance(name, str) or not name.strip():
            raise WorkflowValidationError(
                "Workflow name is required"
            )

        if self.repository.get_by_name(name) is not None:
            raise WorkflowValidationError(
                f"Workflow already exists: {name}"
            )

        return self.repository.create(
            name=name,
            description=description,
            enabled=enabled,
        )

    def get_workflow(
        self,
        workflow_id,
    ):
        workflow = self.repository.get(
            workflow_id
        )

        if workflow is None:
            raise WorkflowNotFoundError(
                f"Workflow does not exist: {workflow_id}"
            )

        return workflow

    def list_workflows(self):
        return self.repository.list()

    def update_workflow(
        self,
        workflow_id,
        name,
        description="",
        enabled=True,
    ):
        self.get_workflow(
            workflow_id
        )

        existing = self.repository.get_by_name(
            name
        )

        if (
            existing is not None
            and existing["id"] != workflow_id
        ):
            raise WorkflowValidationError(
                f"Workflow already exists: {name}"
            )

        return self.repository.update(
            workflow_id=workflow_id,
            name=name,
            description=description,
            enabled=enabled,
        )

    def delete_workflow(
        self,
        workflow_id,
    ):
        self.get_workflow(
            workflow_id
        )

        self.repository.delete(
            workflow_id
        )

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------

    def add_task(
        self,
        workflow_id,
        task_id,
        position,
    ):
        self.get_workflow(
            workflow_id
        )

        self._get_automation_task(
            task_id
        )

        if self.repository.get_task(
            workflow_id,
            task_id,
        ) is not None:
            raise WorkflowValidationError(
                "Task already exists in workflow: "
                f"{task_id}"
            )

        return self.repository.add_task(
            workflow_id=workflow_id,
            task_id=task_id,
            position=position,
        )

    def remove_task(
        self,
        workflow_id,
        task_id,
    ):
        self.get_workflow(
            workflow_id
        )

        self._require_workflow_task(
            workflow_id,
            task_id,
        )

        self.repository.remove_task(
            workflow_id,
            task_id,
        )

    # ------------------------------------------------------------------
    # Dependency operations
    # ------------------------------------------------------------------

    def add_dependency(
        self,
        workflow_id,
        task_id,
        depends_on_task_id,
    ):
        self.get_workflow(
            workflow_id
        )

        self._require_workflow_task(
            workflow_id,
            task_id,
        )

        self._require_workflow_task(
            workflow_id,
            depends_on_task_id,
        )

        if task_id == depends_on_task_id:
            raise WorkflowDependencyCycleError(
                "Workflow dependency would create a cycle: "
                f"{task_id} -> {depends_on_task_id}"
            )

        existing = self.repository.list_task_dependencies(
            workflow_id,
            task_id,
        )

        if any(
            dependency["depends_on_task_id"]
            == depends_on_task_id
            for dependency in existing
        ):
            raise WorkflowValidationError(
                "Workflow dependency already exists: "
                f"{task_id} -> {depends_on_task_id}"
            )

        self._validate_dependency_edge(
            workflow_id,
            task_id,
            depends_on_task_id,
        )

        return self.repository.add_dependency(
            workflow_id=workflow_id,
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
        )

    def remove_dependency(
        self,
        workflow_id,
        task_id,
        depends_on_task_id,
    ):
        self.get_workflow(
            workflow_id
        )

        self._require_workflow_task(
            workflow_id,
            task_id,
        )

        self._require_workflow_task(
            workflow_id,
            depends_on_task_id,
        )

        dependencies = self.repository.list_task_dependencies(
            workflow_id,
            task_id,
        )

        dependency = next(
            (
                item
                for item in dependencies
                if item["depends_on_task_id"]
                == depends_on_task_id
            ),
            None,
        )

        if dependency is None:
            raise WorkflowDependencyNotFoundError(
                "Workflow dependency does not exist: "
                f"{task_id} -> {depends_on_task_id}"
            )

        self.repository.remove_dependency(
            workflow_id,
            task_id,
            depends_on_task_id,
        )

        return dependency

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_workflow(
        self,
        workflow_id,
    ):
        workflow = self.get_workflow(
            workflow_id
        )

        tasks = self.repository.list_tasks(
            workflow_id
        )

        task_ids = {
            task["task_id"]
            for task in tasks
        }

        errors = []

        for task_id in sorted(task_ids):
            try:
                self._get_automation_task(
                    task_id
                )
            except ValueError as error:
                errors.append(
                    str(error)
                )

        dependencies = self.repository.list_dependencies(
            workflow_id
        )

        for dependency in dependencies:
            task_id = dependency["task_id"]
            depends_on_task_id = dependency[
                "depends_on_task_id"
            ]

            if task_id not in task_ids:
                errors.append(
                    "Workflow dependency source task "
                    f"is not in workflow: {task_id}"
                )

            if depends_on_task_id not in task_ids:
                errors.append(
                    "Workflow dependency target task "
                    f"is not in workflow: "
                    f"{depends_on_task_id}"
                )

            if task_id == depends_on_task_id:
                errors.append(
                    "Workflow dependency contains a "
                    f"self-dependency: {task_id}"
                )

        if not errors:
            try:
                self._validate_graph(
                    task_ids,
                    dependencies,
                )
            except WorkflowDependencyCycleError as error:
                errors.append(
                    str(error)
                )

        return {
            "workflow_id": workflow["id"],
            "valid": not errors,
            "errors": errors,
            "task_count": len(tasks),
            "dependency_count": len(dependencies),
        }

    # ------------------------------------------------------------------
    # Internal validation
    # ------------------------------------------------------------------

    def _get_automation_task(
        self,
        task_id,
    ):
        return self.automation_service.find_task(
            task_id
        )

    def _require_workflow_task(
        self,
        workflow_id,
        task_id,
    ):
        task = self.repository.get_task(
            workflow_id,
            task_id,
        )

        if task is None:
            raise WorkflowTaskNotFoundError(
                "Workflow task does not exist: "
                f"{task_id}"
            )

        return task

    def _validate_dependency_edge(
        self,
        workflow_id,
        task_id,
        depends_on_task_id,
    ):
        dependencies = self.repository.list_dependencies(
            workflow_id
        )

        dependencies = list(
            dependencies
        )

        dependencies.append(
            {
                "task_id": task_id,
                "depends_on_task_id": depends_on_task_id,
            }
        )

        task_ids = {
            task["task_id"]
            for task in self.repository.list_tasks(
                workflow_id
            )
        }

        self._validate_graph(
            task_ids,
            dependencies,
        )

    @staticmethod
    def _validate_graph(
        task_ids,
        dependencies,
    ):
        graph = {
            task_id: set()
            for task_id in task_ids
        }

        for dependency in dependencies:
            task_id = dependency["task_id"]
            depends_on_task_id = dependency[
                "depends_on_task_id"
            ]

            if task_id in graph:
                graph[task_id].add(
                    depends_on_task_id
                )

        visiting = set()
        visited = set()

        def visit(task_id):
            if task_id in visiting:
                raise WorkflowDependencyCycleError(
                    "Workflow dependency would create a cycle"
                )

            if task_id in visited:
                return

            visiting.add(task_id)

            for dependency in graph.get(
                task_id,
                (),
            ):
                visit(
                    dependency
                )

            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in graph:
            visit(task_id)
