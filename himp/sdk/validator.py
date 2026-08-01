"""
Plugin Validation Engine.
"""

from himp.models.validation import Validation
from himp.plugins.loader import PluginLoader
from himp.sdk import checks


VALIDATION_CHECKS = [
    ("Plugin Directory", checks.plugin_directory),
    ("Manifest", checks.manifest),
    ("Name", checks.name),
    ("Version", checks.version),
    ("Description", checks.description),
    ("Entrypoint", checks.entrypoint),
    ("Entrypoint File", checks.entrypoint_file),
    ("Requirements", checks.requirements),
    ("Artifacts", checks.artifacts),
]


class PluginValidator:

    def __init__(self):

        self.loader = PluginLoader()

    def validate_plugin(self, name):

        plugin = self.loader.find(name)

        if plugin is None:
            return None

        result = Validation(
            plugin=plugin.id,
            passed=True,
        )

        for check_name, check_function in VALIDATION_CHECKS:

            result.add_check(
                check_name,
                check_function(plugin),
            )

        result.passed = (
            result.failed_checks() == 0
        )

        return result

    def validate_all(self):

        return [
            self.validate_plugin(plugin.id)
            for plugin in self.loader.plugins()
        ]
