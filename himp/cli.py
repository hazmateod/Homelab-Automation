"""
Command Line Interface
"""

import argparse

from himp.commands import (
    automation_run,
    dashboard,
    docs,
    health,
    history,
    inventory,
    inventory_sync,
    plugin,
    plugin_run,
    plugins,
    report,
    status,
    update,
    validate,
)


def main():

    parser = argparse.ArgumentParser(
        prog="himp",
        description="Homelab Infrastructure Management Platform",
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    docs_parser = subparsers.add_parser(
        "docs",
        help="Documentation commands",
    )
    docs_parser.set_defaults(func=docs.run)

    report_parser = subparsers.add_parser(
        "report",
        help="Reporting commands",
    )
    report_parser.add_argument(
        "--limit",
        help="Limit execution to a host or group",
    )
    report_parser.set_defaults(func=report.run)

    health_parser = subparsers.add_parser(
        "health",
        help="Health commands",
    )
    health_parser.set_defaults(func=health.run)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Dashboard commands",
    )
    dashboard_parser.set_defaults(func=dashboard.run)

    status_parser = subparsers.add_parser(
        "status",
        help="Platform status",
    )
    status_parser.set_defaults(func=status.run)

    inventory_parser = subparsers.add_parser(
        "inventory",
        help="Show inventory information",
    )
    inventory_parser.add_argument(
        "hostname",
        nargs="?",
        help="Hostname to display",
    )
    inventory_parser.add_argument(
        "--status",
        choices=[
            "HEALTHY",
            "WARNING",
            "CRITICAL",
            "UNKNOWN",
        ],
        help="Filter hosts by status",
    )
    inventory_parser.set_defaults(
        func=inventory.run,
    )

    inventory_sync_parser = subparsers.add_parser(
        "inventory-sync",
        help="Synchronize inventory with the live Ansible inventory",
    )
    inventory_sync_parser.set_defaults(
        func=inventory_sync.run,
    )

    automation_run_parser = subparsers.add_parser(
        "automation-run",
        help="Run a registered automation task",
    )
    automation_run_parser.add_argument(
        "task_id",
        help="Automation task ID",
    )
    automation_run_parser.set_defaults(
        func=automation_run.run,
    )

    update_parser = subparsers.add_parser(
        "update",
        help="Run maintenance on a host or group",
    )
    update_parser.add_argument(
        "target",
        help="Host or inventory group to update",
    )
    update_parser.set_defaults(
        func=update.run,
    )

    history_parser = subparsers.add_parser(
        "history",
        help="Show command history",
    )
    history_parser.set_defaults(
        func=history.run,
    )

    plugins_parser = subparsers.add_parser(
        "plugins",
        help="List installed plugins",
    )
    plugins_parser.set_defaults(
        func=plugins.run,
    )

    plugin_parser = subparsers.add_parser(
        "plugin",
        help="Show plugin details",
    )
    plugin_parser.add_argument(
        "name",
        help="Plugin name",
    )
    plugin_parser.set_defaults(
        func=plugin.run,
    )

    plugin_run_parser = subparsers.add_parser(
        "plugin-run",
        help="Execute a plugin",
    )
    plugin_run_parser.add_argument(
        "name",
        help="Plugin name",
    )
    plugin_run_parser.set_defaults(
        func=plugin_run.run,
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate installed plugins",
    )
    validate_parser.set_defaults(
        func=validate.run,
    )

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
