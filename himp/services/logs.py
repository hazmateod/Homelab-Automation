"""
HIMP Log Service.

Provides a normalized read-only view across existing operational
execution and audit repositories.
"""

from himp.database.automation_executions import (
    AutomationExecutionRepository,
)
from himp.database.executions import ExecutionRepository
from himp.database.remediation_audit import (
    RemediationAuditRepository,
)
from himp.database.workflow_executions import (
    WorkflowExecutionRepository,
)


class LogService:

    def __init__(
        self,
        automation_executions=None,
        workflow_executions=None,
        executions=None,
        remediation_audit=None,
    ):
        self.automation_executions = (
            automation_executions
            or AutomationExecutionRepository()
        )

        self.workflow_executions = (
            workflow_executions
            or WorkflowExecutionRepository()
        )

        self.executions = (
            executions
            or ExecutionRepository()
        )

        self.remediation_audit = (
            remediation_audit
            or RemediationAuditRepository()
        )

    def history(self, limit=100):
        records = []

        records.extend(
            self._automation_records(
                self.automation_executions.history(
                    limit=limit,
                )
            )
        )

        records.extend(
            self._workflow_records(
                self.workflow_executions.history(
                    limit=limit,
                )
            )
        )

        records.extend(
            self._execution_records(
                self.executions.history(
                    limit=limit,
                )
            )
        )

        records.extend(
            self._remediation_records(
                self.remediation_audit.history(
                    limit=limit,
                )
            )
        )

        records.sort(
            key=lambda record: (
                record["timestamp"] is not None,
                record["timestamp"] or "",
                record["id"],
            ),
            reverse=True,
        )

        return records[:limit]

    def _automation_records(self, executions):
        records = []

        for execution in executions:
            success = execution["success"]

            records.append(
                self._record(
                    record_id=f"automation:{execution['id']}",
                    timestamp=execution["executed_at"],
                    source="automation",
                    event="automation_execution",
                    status=(
                        "success"
                        if success
                        else "failed"
                    ),
                    message=(
                        f"Automation execution: "
                        f"{execution['task_id']}"
                    ),
                    details={
                        "task_id": execution["task_id"],
                        "workflow_execution_id": (
                            execution[
                                "workflow_execution_id"
                            ]
                        ),
                        "elapsed": execution["elapsed"],
                        "result": execution["result"],
                    },
                )
            )

        return records

    def _workflow_records(self, executions):
        records = []

        for execution in executions:
            success = execution["success"]

            if success is None:
                status = "running"
            elif success:
                status = "success"
            else:
                status = "failed"

            records.append(
                self._record(
                    record_id=(
                        f"workflow:"
                        f"{execution['workflow_execution_id']}"
                    ),
                    timestamp=(
                        execution["completed_at"]
                        or execution["started_at"]
                    ),
                    source="workflow",
                    event="workflow_execution",
                    status=status,
                    message=(
                        f"Workflow execution: "
                        f"{execution['workflow_execution_id']}"
                    ),
                    details={
                        "workflow_id": execution["workflow_id"],
                        "workflow_execution_id": (
                            execution[
                                "workflow_execution_id"
                            ]
                        ),
                        "started_at": execution["started_at"],
                        "completed_at": (
                            execution["completed_at"]
                        ),
                        "current_task_id": (
                            execution["current_task_id"]
                        ),
                    },
                )
            )

        return records

    def _execution_records(self, executions):
        records = []

        for execution in executions:
            success = bool(execution["success"])

            records.append(
                self._record(
                    record_id=f"execution:{execution['id']}",
                    timestamp=execution.get(
                        "created_at"
                    ),
                    source="plugin",
                    event="plugin_execution",
                    status=(
                        "success"
                        if success
                        else "failed"
                    ),
                    message=(
                        f"Plugin execution: "
                        f"{execution['plugin']}"
                    ),
                    details={
                        "plugin": execution["plugin"],
                        "return_code": (
                            execution["return_code"]
                        ),
                        "elapsed": execution["elapsed"],
                        "stdout": execution["stdout"],
                        "stderr": execution["stderr"],
                        "warnings": execution["warnings"],
                        "artifacts": execution["artifacts"],
                    },
                )
            )

        return records

    def _remediation_records(self, audits):
        records = []

        for audit in audits:
            if audit["execution_success"] is None:
                status = audit["decision"].lower()
            elif audit["execution_success"]:
                status = "success"
            else:
                status = "failed"

            records.append(
                self._record(
                    record_id=f"remediation:{audit['id']}",
                    timestamp=audit["created_at"],
                    source="remediation",
                    event="remediation_audit",
                    status=status,
                    message=(
                        f"Remediation decision: "
                        f"{audit['decision']}"
                    ),
                    details={
                        "source_type": audit["source_type"],
                        "source_id": audit["source_id"],
                        "task_id": audit["task_id"],
                        "decision": audit["decision"],
                        "reason": audit["reason"],
                        "evidence": audit["evidence"],
                        "risk_level": audit["risk_level"],
                        "confirmation_required": (
                            audit[
                                "confirmation_required"
                            ]
                        ),
                        "confirmed": audit["confirmed"],
                        "execution_id": (
                            audit["execution_id"]
                        ),
                        "execution_success": (
                            audit[
                                "execution_success"
                            ]
                        ),
                    },
                )
            )

        return records

    @staticmethod
    def _record(
        record_id,
        timestamp,
        source,
        event,
        status,
        message,
        details,
    ):
        return {
            "id": record_id,
            "timestamp": timestamp,
            "source": source,
            "event": event,
            "status": status,
            "message": message,
            "details": details,
        }
