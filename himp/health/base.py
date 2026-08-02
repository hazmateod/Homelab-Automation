from __future__ import annotations

from abc import ABC, abstractmethod

from himp.health.models import HealthCheckResult


class HealthCheck(ABC):
    """
    Base class for all HIMP health checks.
    """

    name: str = "Unnamed Health Check"

    @abstractmethod
    async def run(self) -> HealthCheckResult:
        """
        Execute the health check and return the result.
        """
        raise NotImplementedError
