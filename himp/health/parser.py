"""
Health Artifact Parser.
"""

from __future__ import annotations

import json
from pathlib import Path

from himp.health.models import (
    HealthStatus,
    HealthCheckResult,
    HostHealthResult,
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


        #
        # Multi-host health artifact
        #
        if "hosts" in data:

            hosts = []

            total_earned = 0
            total_possible = 0
            issues = []


            for item in data.get("hosts", []):

                health = item.get(
                    "health",
                    {}
                )

                status = STATUS_MAP.get(
                    health.get(
                        "status",
                        "UNKNOWN"
                    ),
                    HealthStatus.UNKNOWN,
                )


                earned = health.get(
                    "earned",
                    0
                )

                possible = health.get(
                    "possible",
                    0
                )

                total_earned += earned
                total_possible += possible

                issues.extend(
                    health.get(
                        "issues",
                        []
                    )
                )


                hosts.append(
                    HostHealthResult(

                        hostname=item.get(
                            "hostname",
                            "unknown"
                        ),

                        results=[

                            HealthCheckResult(

                                plugin=data.get(
                                    "plugin",
                                    path.stem
                                ),

                                check="health",

                                status=status,

                                message=health.get(
                                    "status",
                                    "UNKNOWN"
                                ),

                                details=health,

                            )

                        ],

                    )
                )


            if total_earned == total_possible and total_possible > 0:
                status = HealthStatus.PASS
            elif total_earned > 0:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.FAIL


            return PluginHealthExecution(

                summary=PluginHealthSummary(

                    plugin=data.get(
                        "plugin",
                        path.stem
                    ),

                    status=status,

                    score=total_earned,

                    possible=total_possible,

                    issues=issues,

                ),

                metadata=PluginMetadata(
                    data=data
                ),

                hosts=hosts,

            )


        #
        # Single host artifact
        #

        health = data.get(
            "health",
            {}
        )

        status = STATUS_MAP.get(
            health.get(
                "status",
                "UNKNOWN"
            ),
            HealthStatus.UNKNOWN,
        )


        return PluginHealthExecution(

            summary=PluginHealthSummary(

                plugin=data.get(
                    "plugin",
                    ""
                ),

                status=status,

                score=health.get(
                    "earned",
                    0
                ),

                possible=health.get(
                    "possible",
                    0
                ),

                issues=health.get(
                    "issues",
                    []
                ),

            ),

            metadata=PluginMetadata(
                data=data.get(
                    "report",
                    {}
                )
            ),

        )
