"""
Base Generator.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment
from jinja2 import FileSystemLoader


class Generator:

    def __init__(self):

        self.project_root = Path.cwd()

        self.template_root = (
            self.project_root /
            "tools" /
            "templates"
        )

        self.environment = Environment(
            loader=FileSystemLoader(
                self.template_root
            ),
            keep_trailing_newline=True,
            autoescape=False,
        )

    def mkdir(self, path):

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def render(
        self,
        template,
        destination,
        **context,
    ):

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        rendered = (
            self.environment
            .get_template(template)
            .render(**context)
        )

        destination.write_text(
            rendered,
            encoding="utf-8",
        )

        print(f"Created {destination}")
