#!/usr/bin/env python3
"""
HIMP Command Line Interface
"""

import argparse

from himp.commands import docs, report, health

def docs_command(args):
    docs.run(args)

def report_command(args):
    report.run(args)


def health_command(args):
    health.run(args)

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

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
