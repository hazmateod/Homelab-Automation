"""
Reporting Commands
"""

from himp.config import config
from himp.lib.ansible import run_playbook
from himp.lib.history import log
from himp.lib.output import error, info, success


def run(args):

    info("Generating reports...")
    print()

    result = run_playbook(
        config.report_playbook,
        args.limit,
    )

    log(
        "report",
        result.success,
        result.elapsed,
    )

    print()

    if ok:
        success("Report generation completed successfully.")
    else:
        error("Report generation failed.")

    info(f"Execution time: {elapsed:.2f} seconds")
