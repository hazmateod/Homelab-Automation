from __future__ import annotations

import asyncio
from time import perf_counter

from himp.health.base import HealthCheck
from himp.health.models import HealthCheckResult


class HealthRunner:
    """
    Executes registered health checks concurrently.
    """

    def __init__(self) -> None:
        self._checks: list[HealthCheck] = []

    def register(self, check: HealthCheck) -> None:
        self._checks.append(check)

    async def run(self) -> list[HealthCheckResult]:
        if not self._checks:
            return []

        async def execute(check: HealthCheck) -> HealthCheckResult:
            start = perf_counter()

            result = await check.run()

            result.duration_ms = round(
                (perf_counter() - start) * 1000,
                2,
            )

            return result

        return await asyncio.gather(
            *(execute(check) for check in self._checks)
        )
