"""
Scheduler Run Command.
"""

import sys
from datetime import datetime

from himp.app import HIMP
from himp.services.scheduler import SchedulerService


def run(args):
    himp = HIMP()
    scheduler = SchedulerService()

    if args.at:
        try:
            now = datetime.fromisoformat(
                args.at
            )
        except ValueError as exc:
            print(
                "Invalid --at value. "
                "Use ISO format such as "
                "2026-08-09T03:00:00.",
                file=sys.stderr,
            )
            return 2
    else:
        now = datetime.now()

    due_tasks = scheduler.due_tasks(now)

    print(
        f"Scheduler evaluation time: "
        f"{now.isoformat()}"
    )
    print(
        f"Due tasks: {len(due_tasks)}"
    )

    if not due_tasks:
        print("No scheduled tasks are due.")
        return 0

    failed = False

    for schedule in due_tasks:
        task_id = schedule["task_id"]

        print()
        print(
            f"=== RUNNING {task_id} ==="
        )

        try:
            result = himp.automation.run(
                task_id
            )

            task_result = result.get(
                "result",
                {},
            )

            if isinstance(
                task_result,
                dict,
            ) and task_result.get(
                "success",
                True,
            ) is False:
                failed = True

                print(
                    "Automation task failed."
                )
                print(
                    f"Task       : {result['task']}"
                )
                print(
                    f"Executed   : {result['executed_at']}"
                )
                print(
                    f"Error      : "
                    f"{task_result.get('error', 'Unknown error')}",
                    file=sys.stderr,
                )

                continue

            scheduler.record_run(
                task_id
            )

            print(
                "Automation task completed successfully."
            )
            print(
                f"Task       : {result['task']}"
            )
            print(
                f"Executed   : {result['executed_at']}"
            )

        except Exception as exc:
            failed = True

            print(
                f"Automation task failed: {exc}",
                file=sys.stderr,
            )

    if failed:
        return 1

    print()
    print(
        "Scheduler run completed successfully."
    )

    return 0
