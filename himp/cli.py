#!/usr/bin/env python3
"""
HIMP Command Line Interface
"""

import argparse

from himp.commands import docs, report, health, dashboard, status

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

def main():

    parser = argparse.ArgumentParser(
        prog="himp",
        description="Homelab Infrastructure Management Platform",
    )

    subparsers = parser.add_subparsers(dest="command")

    docs = subparsers.add_parser(
        "docs",
        help="Documentation commands",
    )
    docs.set_defaults(func=docs_command)

    report = subparsers.add_parser(
        "report",
        help="Reporting commands",
    )
    report.set_defaults(func=report_command)

    health = subparsers.add_parser(
        "health",
        help="Health commands",
    )
    health.set_defaults(func=health_command)

    dashboard = subparsers.add_parser(
        "dashboard",
        help="Dashboard commands",
    )
    dashboard.set_defaults(func=dashboard_command)

    status = subparsers.add_parser(
        "status",
        help="Platform status",
    )
    status.set_defaults(func=status_command)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
