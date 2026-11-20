"""
Update Commands
"""

from himp.lib.history import log
from himp.lib.output import error, info, success
from himp.app import HIMP


def run(args):
    if not args.target:
        error("Host or group is required.")
        return

    if args.target != "maintenance":
        error("Use the automation API for explicit host or group updates.")
        return 1

    service = HIMP().automation

    info(f"Updating {args.target}...")
    print()

    execution = service.run("scheduled_updates", confirmed=True)
    result = execution["result"]

    ok = result["success"]
    elapsed = result["elapsed"]

    log(
        f"update {args.target}",
        ok,
        elapsed,
    )

    print()

    if ok:
        success("Update completed successfully.")
    else:
        error("Update failed.")

    info(f"Execution time: {elapsed:.2f} seconds")
    return 0 if ok else 1
