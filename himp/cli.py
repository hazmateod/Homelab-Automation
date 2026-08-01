#!/usr/bin/env python3
"""
HIMP Command Line Interface
"""

import argparse

from himp.commands import (
    dashboard,
    docs,
    health,
    history,
    inventory,
    plugins,
    report,
    status,
    update,
)


def docs_command(args):
    docs.run(args)


def report_command(args):
    report.run(args)


def health_command(args):
    health.run(args)


def dashboard_command(args):
    dashboard.run(args)


def status_command(args):
    status.run(args)


def inventory_command(args):
    inventory.run(args)


def update_command(args):
    update.run(args)


def history_command(args):
    history.run(args)


def plugins_command(args):
    plugins.run(args)


def main():

    parser = argparse.ArgumentParser(
        prog="himp",
        description="Homelab Infrastructure Management Platform",
    )

    subparsers = parser.add_subparsers(dest="command")

    docs_parser = subparsers.add_parser(
        "docs",
        help="Documentation commands",
    )
    docs_parser.set_defaults(func=docs_command)

    report_parser = subparsers.add_parser(
        "report",
        help="Reporting commands",
    )
    report_parser.add_argument(
        "--limit",
        help="Limit execution to a host or group",
    )
    report_parser.set_defaults(func=report_command)

    health_parser = subparsers.add_parser(
        "health",
        help="Health commands",
    )
    health_parser.set_defaults(func=health_command)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Dashboard commands",
    )
    dashboard_parser.set_defaults(func=dashboard_command)

    status_parser = subparsers.add_parser(
        "status",
        help="Platform status",
    )
    status_parser.set_defaults(func=status_command)

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

    inventory_parser.set_defaults(func=inventory_command)

    update_parser = subparsers.add_parser(
        "update",
        help="Run maintenance on a host or group",
    )

    update_parser.add_argument(
        "target",
        help="Host or inventory group to update",
    )

    update_parser.set_defaults(func=update_command)

    history_parser = subparsers.add_parser(
        "history",
        help="Show command history",
    )

    history_parser.set_defaults(func=history_command)

    plugins_parser = subparsers.add_parser(
        "plugins",
        help="Show installed plugins",
    )

    plugins_parser.set_defaults(func=plugins_command)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
