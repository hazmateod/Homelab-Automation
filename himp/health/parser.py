"""
Health Artifact Parser.
"""

from __future__ import annotations

import json
from pathlib import Path

from himp.health.models import (
    HealthStatus,
    PluginHealthExecution,
    PluginHealthSummary,
    PluginMetadata,
)


STATUS_MAP = {
    "HEALTHY": HealthStatus.PASS,
    "WARNING": HealthStatus.WARNING,
    "CRITICAL": HealthStatus.FAIL,
    "PASS": HealthStatus.PASS,
    "FAIL": HealthStatus.FAIL,
    "UNKNOWN": HealthStatus.UNKNOWN,
}


class HealthArtifactParser:

    def parse(self, artifact):

        path = Path(artifact)

        if not path.exists():
            return None

        with path.open(
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        health = data.get("health", {})
        report = data.get("report", {})

        status = STATUS_MAP.get(
            health.get("status", "UNKNOWN"),
            HealthStatus.UNKNOWN,
        )

        return PluginHealthExecution(

            summary=PluginHealthSummary(

                plugin=data.get("plugin", ""),

                status=status,

                score=health.get(
                    "earned",
                    0,
                ),

                possible=health.get(
                    "possible",
                    0,
                ),

                issues=health.get(
                    "issues",
                    [],
                ),

            ),

            metadata=PluginMetadata(
                data=report,
            ),

        )
