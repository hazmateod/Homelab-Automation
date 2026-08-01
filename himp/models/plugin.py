"""
Plugin model.
"""

from dataclasses import dataclass


@dataclass
class Plugin:
    name: str
    version: str
    description: str
    enabled: bool = True

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def is_enabled(self):
        return self.enabled
