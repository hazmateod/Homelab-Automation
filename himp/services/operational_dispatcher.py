"""
Operational Dispatcher.

Routes scheduled operational tasks to their existing owning services.
Does not implement scheduling or automation execution.
"""

from datetime import datetime

from himp.services.automation import (
    AutomationService,
)
from himp.services.remediation_autonomous_execution import (
    RemediationAutonomousExecutionService,
)
from himp.services.remediation_autonomous_workflow import (
    RemediationAutonomousWorkflowService,
)
from himp.services.remediation_autonomy import (
    RemediationAutonomyPolicyService,
)
from himp.services.remediation_execution import (
    RemediationExecutionService,
)
from himp.services.remediation_operations import (
    RemediationOperationsService,
)
from himp.services.remediation_policy import (
    RemediationPolicyService,
)
from himp.services.remediation_recommendations import (
    RemediationRecommendationService,
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
        remediation_autonomous_workflow=None,
    ):
        self.automation = automation

        self.remediation_operations = (
            remediation_operations
            if remediation_operations is not None
            else RemediationOperationsService()
        )

        # Keep the legacy constructor argument for test/API
        # compatibility, but scheduled remediation_operations now
        # route through the fail-closed autonomous recommendation
        # workflow.
        self.remediation_workflow = (
            remediation_workflow
        )

        if (
            remediation_autonomous_workflow
            is not None
        ):
            self.remediation_autonomous_workflow = (
                remediation_autonomous_workflow
            )

        else:
            autonomy = (
                RemediationAutonomyPolicyService(
                    automation=automation,
                )
            )

            recommendations = (
                RemediationRecommendationService(
                    autonomy=autonomy,
                )
            )

            policy = RemediationPolicyService(
                automation=automation,
            )

            remediation_execution = (
                RemediationExecutionService(
                    policy=policy,
                    automation=automation,
                )
            )

            autonomous_execution = (
                RemediationAutonomousExecutionService(
                    autonomy=autonomy,
                    execution=remediation_execution,
                )
            )

            self.remediation_autonomous_workflow = (
                RemediationAutonomousWorkflowService(
                    recommendations=recommendations,
                    execution=autonomous_execution,
                )
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

            result = (
                self.remediation_autonomous_workflow.run(
                    source_type=configuration[
                        "source_type"
                    ],
                    source_id=configuration[
                        "source_id"
                    ],
                    baseline=configuration[
                        "baseline"
                    ],
                    change_limit=configuration[
                        "change_limit"
                    ],
                )
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
