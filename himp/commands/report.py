"""
Reporting Commands
"""

from himp.config import config
from himp.database.host_identity import HostIdentityRepository
from himp.lib.ansible import run_playbook
from himp.lib.history import log
from himp.lib.output import error, info, success
from himp.services.inventory_publication import inventory_admission


def run(args):

    info("Generating reports...")
    print()

    with inventory_admission(config.inventory):
        bindings = HostIdentityRepository().execution_bindings()
        options = {"extra_vars": {"himp_host_bindings": bindings}} if bindings else {}
        result = run_playbook(
            config.report_playbook,
            args.limit,
            **options,
        )

    log(
        "report",
        result.success,
        result.elapsed,
    )

    print()

    if result.success:
        success("Report generation completed successfully.")
    else:
        error("Report generation failed.")

    info(f"Execution time: {result.elapsed:.2f} seconds")
