"""
Validation Service.
"""

from himp.sdk.validator import PluginValidator


class ValidationService:

    def __init__(self):

        self.validator = PluginValidator()


    def validate(self, plugin):

        return self.validator.validate_plugin(plugin)


    def validate_all(self):

        return self.validator.validate_all()
