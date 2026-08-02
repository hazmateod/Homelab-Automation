"""
{{ display_name }} Dashboard.
"""

from __future__ import annotations


class {{ class_name }}Dashboard:
    """
    {{ display_name }} dashboard.
    """

    def __init__(self):

        self._widgets = []

    def add_widget(
        self,
        widget,
    ):

        self._widgets.append(widget)

    def widgets(self):

        return list(self._widgets)

    def summary(self):

        return {
            "dashboard": "{{ class_name }}",
            "widget_count": len(self._widgets),
        }
