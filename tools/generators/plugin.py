"""
Plugin Generator.
"""

from __future__ import annotations

from .base import Generator


class PluginGenerator(Generator):

    def generate(self, name):

        display_name = (
            name.replace("_", " ")
            .replace("-", " ")
            .title()
        )

        plugin_dir = (
            self.project_root /
            "plugins" /
            name
        )

        context = {
            "name": name,
            "display_name": display_name,
            "inventory_group": name,
        }

        templates = {
            "plugin/README.md.tpl":
                plugin_dir / "README.md",

            "plugin/plugin.yml.tpl":
                plugin_dir / "plugin.yml",

            "plugin/tasks/main.yml.tpl":
                plugin_dir / "tasks/main.yml",

            "plugin/tasks/discovery.yml.tpl":
                plugin_dir / "tasks/discovery.yml",

            "plugin/tasks/health.yml.tpl":
                plugin_dir / "tasks/health.yml",

            "plugin/tasks/report.yml.tpl":
                plugin_dir / "tasks/report.yml",

            "plugin/tests/validate.yml.tpl":
                plugin_dir / "tests/validate.yml",
        }

        for template, destination in templates.items():

            self.render(
                template,
                destination,
                **context,
            )

        print()
        print(f"Plugin '{name}' generated successfully.")
