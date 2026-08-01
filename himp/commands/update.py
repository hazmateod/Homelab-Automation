"""
Update Commands
"""

from himp.config import config
from himp.lib.ansible import run_playbook
from himp.lib.history import log
from himp.lib.output import error, info, success


def run(args):

    if not args.target:
        error("Host or group is required.")
        return

    info(f"Updating {args.target}...")
    print()

    ok, elapsed = run_playbook(
        config.maintenance_playbook,
        args.target,
    )

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
