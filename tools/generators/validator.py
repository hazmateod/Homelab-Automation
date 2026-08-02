"""
Template Validator.
"""

from __future__ import annotations

from pathlib import Path

import yaml


class TemplateValidator:

    def __init__(self):

        self.template_root = (
            Path.cwd() /
            "tools" /
            "templates"
        )

    def validate(
        self,
        generator_type,
    ):

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
        ) as stream:

            definition = yaml.safe_load(stream)

        required = (
            "type",
            "directories",
            "files",
        )

        for key in required:

            if key not in definition:

                raise ValueError(
                    f"Manifest missing '{key}'"
                )

        for file in definition["files"]:

            template = (
                self.template_root /
                file["template"]
            )

            if not template.exists():

                raise FileNotFoundError(
                    f"Missing template: {template}"
                )

        return True
