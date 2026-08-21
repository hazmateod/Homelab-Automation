"""
Scheduler Run Command.

Evaluates recurring HIMP automation schedules and one-time approved
remediation schedules through the existing scheduler process.
"""

import sys
from datetime import datetime, timezone

from himp.app import HIMP
from himp.database.postgresql import PostgreSQLDatabase
from himp.services.operational_dispatcher import (
    OperationalDispatcher,
)
from himp.services.remediation_scheduling import (
    RemediationSchedulingService,
)
from himp.services.scheduler import SchedulerService


def _utc_naive(value):
    """
    Convert a scheduler evaluation datetime to UTC-naive form for
    remediation schedule persistence comparisons.

    Existing recurring automation schedules intentionally continue to
    use the scheduler's established local-time contract.
    """

    if value.tzinfo is None:
        value = value.astimezone()

    return value.astimezone(
        timezone.utc
    ).replace(
        tzinfo=None
    )


def run(args):
    try:
        himp = HIMP()

        scheduler = SchedulerService()

        remediation_scheduling = (
            RemediationSchedulingService()
        )

        dispatcher = OperationalDispatcher(
            automation=himp.automation,
        )

        if args.at:
            try:
                now = datetime.fromisoformat(
                    args.at
                )
            except ValueError:
                print(
                    "Invalid --at value. "
                    "Use ISO format such as "
                    "2026-08-09T03:00:00.",
                    file=sys.stderr,
                )
                return 2
        else:
            now = datetime.now()

        remediation_now = _utc_naive(
            now
        )

        due_tasks = scheduler.due_tasks(
            now
        )

        due_remediations = (
            remediation_scheduling.due(
                now=remediation_now
            )
        )

        print(
            f"Scheduler evaluation time: "
            f"{now.isoformat()}"
        )

        print(
            f"Due tasks: {len(due_tasks)}"
        )

        print(
            "Due remediation schedules: "
            f"{len(due_remediations)}"
        )

        if (
            not due_tasks
            and not due_remediations
        ):
            print(
                "No scheduled work is due."
            )
            return 0

        failed = False

        # -------------------------------------------------------------
        # Existing recurring automation schedules
        # -------------------------------------------------------------

        for schedule in due_tasks:
            task_id = schedule[
                "task_id"
            ]

            print()

            print(
                f"=== RUNNING {task_id} ==="
            )

            try:
                result = dispatcher.dispatch(
                    task_id
                )

                task_result = result.get(
                    "result",
                    {},
                )

                if (
                    isinstance(
                        task_result,
                        dict,
                    )
                    and task_result.get(
                        "success",
                        True,
                    ) is False
                ):
                    failed = True

                    print(
                        "Automation task failed."
                    )

                    print(
                        f"Task       : "
                        f"{result['task']}"
                    )

                    print(
                        f"Executed   : "
                        f"{result['executed_at']}"
                    )

                    print(
                        "Error      : "
                        f"{task_result.get(
                            'error',
                            'Unknown error',
                        )}",
                        file=sys.stderr,
                    )

                    continue

                scheduler.record_run(
                    task_id
                )

                print(
                    "Automation task completed "
                    "successfully."
                )

                print(
                    f"Task       : "
                    f"{result['task']}"
                )

                print(
                    f"Executed   : "
                    f"{result['executed_at']}"
                )

            except Exception as exc:
                failed = True

                print(
                    "Automation task failed: "
                    f"{exc}",
                    file=sys.stderr,
                )

        # -------------------------------------------------------------
        # Phase 13.3 one-time approved remediation schedules
        # -------------------------------------------------------------

        for schedule in due_remediations:
            schedule_id = schedule[
                "id"
            ]

            approval_id = schedule[
                "approval_id"
            ]

            print()

            print(
                "=== RUNNING REMEDIATION "
                f"SCHEDULE {schedule_id} ==="
            )

            print(
                f"Approval   : {approval_id}"
            )

            print(
                "Scheduled  : "
                f"{schedule['scheduled_for']}"
            )

            try:
                result = (
                    remediation_scheduling.execute_due(
                        schedule_id=schedule_id,
                        now=remediation_now,
                    )
                )

                if result is None:
                    print(
                        "Remediation schedule was not "
                        "claimable; skipping."
                    )
                    continue

                print(
                    f"Status     : "
                    f"{result['status']}"
                )

                if result[
                    "status"
                ] == "FAILED":
                    failed = True

                    print(
                        "Error      : "
                        f"{result.get(
                            'error',
                            'Unknown error',
                        )}",
                        file=sys.stderr,
                    )

                    continue

                if result[
                    "status"
                ] == "COMPLETED":
                    print(
                        "Remediation completed "
                        "successfully."
                    )

                    if result.get(
                        "audit_id"
                    ) is not None:
                        print(
                            "Audit      : "
                            f"{result['audit_id']}"
                        )

            except Exception as exc:
                failed = True

                print(
                    "Remediation schedule failed: "
                    f"{exc}",
                    file=sys.stderr,
                )

        if failed:
            return 1

        print()

        print(
            "Scheduler run completed "
            "successfully."
        )

        return 0

    finally:
        PostgreSQLDatabase.close_pools()
