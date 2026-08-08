"""
Update Commands
"""

from himp.lib.history import log
from himp.lib.output import error, info, success
from himp.services.update import UpdateService


def run(args):
    if not args.target:
        error("Host or group is required.")
        return

    service = UpdateService()

    info(f"Updating {args.target}...")
    print()

    result = service.update(args.target)

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
