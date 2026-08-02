"""
Generator Registry.
"""

from __future__ import annotations

from pathlib import Path


class GeneratorRegistry:

    def __init__(self):

        self.template_root = (
            Path.cwd() /
            "tools" /
            "templates"
        )

    def types(self):

        return sorted(
            directory.name
            for directory in self.template_root.iterdir()
            if directory.is_dir()
            and (directory / "manifest.yml").exists()
        )

    def exists(
        self,
        generator_type,
    ):

        return generator_type in self.types()
