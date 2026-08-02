"""
{{ display_name }} Report.
"""

from __future__ import annotations


class {{ class_name }}Report:
    """
    {{ display_name }} report.
    """

    def __init__(self):

        self._data = {}

    def build(self):

        return {
            "report": "{{ class_name }}",
            "status": "ok",
            "data": self._data,
        }
