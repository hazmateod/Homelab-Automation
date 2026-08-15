"""
Operational Dispatcher.

Routes scheduled operational tasks to their existing owning services.
Does not implement scheduling or automation execution.
"""

from datetime import datetime

from himp.services.remediation_operations import (
    RemediationOperationsService,
)
from himp.services.remediation_workflow import (
    RemediationWorkflowService,
)


class OperationalDispatcher:
    """
    Dispatches operational tasks without owning execution.
    """

    REMEDIATION_TASK_ID = "remediation_operations"

    def __init__(
        self,
        automation,
        remediation_operations=None,
        remediation_workflow=None,
    ):
        self.automation = automation

        self.remediation_operations = (
            remediation_operations
            if remediation_operations is not None
            else RemediationOperationsService()
        )

        self.remediation_workflow = (
            remediation_workflow
            if remediation_workflow is not None
            else RemediationWorkflowService()
        )

    def dispatch(
        self,
        task_id,
    ):
        if task_id == self.REMEDIATION_TASK_ID:
            configuration = self.remediation_operations.get()

            executed_at = datetime.now().isoformat()

            if not configuration:
                return {
                    "task": task_id,
                    "executed_at": executed_at,
                    "success": False,
                    "error_category": "configuration",
                    "result": {
                        "success": False,
                        "error": (
                            "Remediation operational "
                            "configuration is not configured."
                        ),
                    },
                }

            if not configuration["enabled"]:
                return {
                    "task": task_id,
                    "executed_at": executed_at,
                    "success": True,
                    "skipped": True,
                    "result": {
                        "success": True,
                        "skipped": True,
                        "reason": (
                            "Remediation operations are disabled."
                        ),
                    },
                }

            result = self.remediation_workflow.run(
                source_type=configuration["source_type"],
                source_id=configuration["source_id"],
                baseline=configuration["baseline"],
                change_limit=configuration["change_limit"],
                confirmed=False,
            )

            return {
                "task": task_id,
                "executed_at": executed_at,
                "success": True,
                "result": result,
            }

        result = self.automation.run(
            task_id
        )

        return result
