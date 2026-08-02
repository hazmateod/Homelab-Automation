"""
Generic Template Generator.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from jinja2 import Template

from .plan import GenerationPlan


class GenericGenerator:

    def __init__(self):

        self.project_root = Path.cwd()

        self.template_root = (
            self.project_root /
            "tools" /
            "templates"
        )

    def build_plan(
        self,
        generator_type,
        **context,
    ):

        context.setdefault(
            "display_name",
            context["name"]
            .replace("_", " ")
            .replace("-", " ")
            .title(),
        )

        context.setdefault(
            "inventory_group",
            context["name"],
        )

        context.setdefault(
            "class_name",
            "".join(
                word.capitalize()
                for word in context["name"]
                .replace("-", "_")
                .split("_")
            ),
        )

        manifest = (
            self.template_root /
            generator_type /
            "manifest.yml"
        )

        if not manifest.exists():
            raise FileNotFoundError(
                f"Missing manifest: {manifest}"
            )

        with manifest.open(
            encoding="utf-8",
        ) as f:

            definition = yaml.safe_load(f)

        for variable in definition.get(
            "variables",
            [],
        ):

            name = variable["name"]

            if (
                variable.get("required", False)
                and name not in context
            ):
                raise ValueError(
                    f"Missing required variable: {name}"
                )

        plan = GenerationPlan()

        for directory in definition.get(
            "directories",
            [],
        ):

            plan.add_directory(
                Template(directory).render(
                    **context,
                )
            )

        for file in definition.get(
            "files",
            [],
        ):

            plan.add_file(
                file["template"],
                Template(
                    file["destination"]
                ).render(
                    **context,
                ),
            )

        return plan, context
