"""
{{ display_name }} Model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class {{ class_name }}:
    """
    {{ display_name }} model.
    """

    name: str

    enabled: bool = True

    def summary(self):

        return {
            "name": self.name,
            "enabled": self.enabled,
        }
