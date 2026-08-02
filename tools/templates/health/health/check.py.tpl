"""
{{ display_name }} Health Check.
"""

from __future__ import annotations

from himp.health.base import HealthCheck
from himp.health.models import (
    HealthCheckResult,
    HealthStatus,
)


class {{ class_name }}HealthCheck(HealthCheck):
    """
    {{ display_name }} health check.
    """

    name = "{{ display_name }}"

    async def run(self) -> HealthCheckResult:

        return HealthCheckResult(
            plugin="{{ name }}",
            check=self.name,
            status=HealthStatus.PASS,
            message="{{ display_name }} health check passed.",
        )
