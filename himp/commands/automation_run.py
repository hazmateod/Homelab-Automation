"""
Automation Run Command.
"""

import sys

from himp.app import HIMP


def run(args):
    himp = HIMP()

    try:
        result = himp.automation.run(args.task_id)
    except Exception as exc:
        print(
            f"Automation task failed: {exc}",
            file=sys.stderr,
        )
        return 1

    task_result = result["result"]

    print("Automation task completed successfully.")
    print(f"Task       : {result['task']}")
    print(f"Executed   : {result['executed_at']}")
    print(f"Target     : {task_result.get('target', 'n/a')}")
    print(f"Success    : {task_result.get('success', 'n/a')}")
    print(f"Elapsed    : {task_result.get('elapsed', 'n/a')}")

    return 0
