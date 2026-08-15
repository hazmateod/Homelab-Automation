"""
Dashboard Commands
"""

from himp.config import config
from himp.lib.ansible import run_playbook
from himp.lib.history import log
from himp.lib.output import error, info, success


def run(args):

    info("Generating dashboard...")
    print()

    result = run_playbook(
        config.dashboard_playbook,
    )

    log(
        "dashboard",
        result.success,
        result.elapsed,
    )

    print()

    if result.success:
        success("Dashboard generation completed successfully.")
    else:
        error("Dashboard generation failed.")

    info(f"Execution time: {result.elapsed:.2f} seconds")
