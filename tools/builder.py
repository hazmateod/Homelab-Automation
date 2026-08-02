#!/usr/bin/env python3
"""
HIMP Builder
"""

from __future__ import annotations

import argparse
import sys

from generators.registry import GeneratorRegistry
from generators.service import BuilderService


def build_parser():

    parser = argparse.ArgumentParser(
        prog="builder",
        description="HIMP Builder",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    generate = subparsers.add_parser(
        "generate",
        help="Generate from templates",
    )

    generate.add_argument("type")
    generate.add_argument("name")

    dry_run = subparsers.add_parser(
        "dry-run",
        help="Preview generated files",
    )

    dry_run.add_argument("type")
    dry_run.add_argument("name")

    validate = subparsers.add_parser(
        "validate",
        help="Validate a generator",
    )

    validate.add_argument("type")

    subparsers.add_parser(
        "list",
        help="List available generators",
    )

    return parser


def banner():

    print()
    print("========================================")
    print(" HIMP Builder")
    print("========================================")
    print()


def print_plan(plan):

    print("Directories")
    print("-----------")

    for directory in plan.directories:
        print(directory)

    print()
    print("Files")
    print("-----")

    for _, destination in plan.files:
        print(destination)

    print()
    print(
        f"Summary: {plan.directory_count} directories, "
        f"{plan.file_count} files"
    )


def main():

    parser = build_parser()

    args = parser.parse_args()

    registry = GeneratorRegistry()

    service = BuilderService()

    banner()

    if args.command == "list":

        print("Available Generators")
        print("--------------------")

        for generator in registry.types():
            print(generator)

        return 0

    if args.command == "validate":

        service.validate(args.type)

        print(f"{args.type} validated successfully.")

        return 0

    if not registry.exists(args.type):

        print(f"Unknown generator: {args.type}")

        return 1

    if args.command == "dry-run":

        plan = service.dry_run(
            args.type,
            name=args.name,
        )

        print_plan(plan)

        return 0

    if args.command == "generate":

        service.generate(
            args.type,
            name=args.name,
        )

        return 0

    return 0


if __name__ == "__main__":

    sys.exit(main())
