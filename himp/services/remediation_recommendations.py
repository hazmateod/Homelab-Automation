"""
Evidence-backed Remediation Recommendations.

Translates deterministic HIMP health and dependency intelligence into
operator recommendations without executing automation.

Phase 13.1 is intentionally read-only. Recommendation generation does
not create remediation audit records, modify infrastructure state, or
invoke the remediation execution workflow.
"""

from himp.services.dependency_impact import (
    DependencyImpactService,
)
from himp.services.health_analysis import (
    HealthAnalysisService,
)


class RemediationRecommendationService:
    """
    Generate deterministic operator remediation recommendations.
    """

    SEVERITY_ORDER = {
        "CRITICAL": 0,
        "WARNING": 1,
        "INFO": 2,
    }

    def __init__(
        self,
        health=None,
        impact=None,
    ):
        self.health = (
            health
            if health is not None
            else HealthAnalysisService()
        )

        self.impact = (
            impact
            if impact is not None
            else DependencyImpactService()
        )

    @staticmethod
    def _validate_entity(
        entity_type,
        entity_id,
    ):
        if (
            not isinstance(entity_type, str)
            or not entity_type.strip()
        ):
            raise ValueError(
                "entity_type must not be empty"
            )

        if (
            not isinstance(entity_id, str)
            or not entity_id.strip()
        ):
            raise ValueError(
                "entity_id must not be empty"
            )

        return (
            entity_type.strip(),
            entity_id.strip(),
        )

    @staticmethod
    def _evidence(
        analysis,
    ):
        """
        Return the bounded historical evidence relevant to an operator.
        """

        return {
            "history_available": analysis[
                "history_available"
            ],
            "observation_count": analysis[
                "observation_count"
            ],
            "current_status": analysis[
                "current_status"
            ],
            "current_state": analysis[
                "current_state"
            ],
            "current_streak": analysis[
                "current_streak"
            ],
            "failure_percentage": analysis[
                "failure_percentage"
            ],
            "unhealthy_percentage": analysis[
                "unhealthy_percentage"
            ],
            "transition_count": analysis[
                "transition_count"
            ],
            "flap_count": analysis[
                "flap_count"
            ],
            "is_flapping": analysis[
                "is_flapping"
            ],
            "latest_observation": analysis[
                "latest_observation"
            ],
        }

    @staticmethod
    def _unhealthy_severity(
        analysis,
    ):
        """
        Escalate deterministic failure evidence without prediction.
        """

        if (
            analysis["current_status"] == "FAIL"
            or analysis["failure_percentage"] >= 50.0
        ):
            return "CRITICAL"

        return "WARNING"

    def _affected_assets(
        self,
        hostname,
    ):
        """
        Determine reverse dependency impact for the unhealthy host.
        """

        impact = self.impact.impact(
            entity_type="host",
            entity_id=hostname,
        )

        return impact["assets"]

    def _unhealthy_recommendation(
        self,
        hostname,
        analysis,
        depth,
        path,
    ):
        severity = self._unhealthy_severity(
            analysis
        )

        current_status = (
            analysis["current_status"]
            or "UNKNOWN"
        )

        return {
            "recommendation_id": (
                f"HOST_UNHEALTHY:{hostname}"
            ),
            "condition": "HOST_UNHEALTHY",
            "severity": severity,
            "target": {
                "entity_type": "host",
                "entity_id": hostname,
            },
            "dependency_depth": depth,
            "dependency_path": path,
            "evidence": self._evidence(
                analysis
            ),
            "affected_assets": (
                self._affected_assets(
                    hostname
                )
            ),
            "recommended_action": (
                "Investigate host connectivity and service health "
                "before selecting or executing remediation."
            ),
            "rationale": (
                f"{hostname} currently reports "
                f"{current_status} health with "
                f"{analysis['observation_count']} persisted "
                "observation(s). Review the failing condition and "
                "its affected dependencies before taking action."
            ),
            "automation": None,
            "execution_permitted": False,
        }

    def _flapping_recommendation(
        self,
        hostname,
        analysis,
        depth,
        path,
    ):
        return {
            "recommendation_id": (
                f"HOST_FLAPPING:{hostname}"
            ),
            "condition": "HOST_FLAPPING",
            "severity": "WARNING",
            "target": {
                "entity_type": "host",
                "entity_id": hostname,
            },
            "dependency_depth": depth,
            "dependency_path": path,
            "evidence": self._evidence(
                analysis
            ),
            "affected_assets": (
                self._affected_assets(
                    hostname
                )
            ),
            "recommended_action": (
                "Investigate intermittent connectivity or service "
                "instability and review recent state transitions "
                "before remediation."
            ),
            "rationale": (
                f"{hostname} has crossed the bounded HIMP flapping "
                f"threshold with {analysis['transition_count']} "
                "state transition(s). Repeated state changes should "
                "be understood before applying a corrective action."
            ),
            "automation": None,
            "execution_permitted": False,
        }

    def _recommend_for_host(
        self,
        hostname,
        analysis,
        depth,
        path,
    ):
        """
        Generate zero or more deterministic findings for one host.
        """

        if not analysis["history_available"]:
            return []

        recommendations = []

        if analysis["current_state"] == "UNHEALTHY":
            recommendations.append(
                self._unhealthy_recommendation(
                    hostname=hostname,
                    analysis=analysis,
                    depth=depth,
                    path=path,
                )
            )

        if analysis["is_flapping"]:
            recommendations.append(
                self._flapping_recommendation(
                    hostname=hostname,
                    analysis=analysis,
                    depth=depth,
                    path=path,
                )
            )

        return recommendations

    def recommend(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        """
        Return evidence-backed recommendations for an asset.

        For applications/services/databases and other graph entities,
        historical health is evaluated for reachable host dependencies.

        For a host root, the host's own health is also evaluated.

        No automation execution occurs.
        """

        (
            entity_type,
            entity_id,
        ) = self._validate_entity(
            entity_type,
            entity_id,
        )

        correlation = self.health.correlate(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

        recommendations = []

        seen_hosts = set()

        for host in correlation["hosts"]:
            hostname = host["hostname"]

            seen_hosts.add(
                hostname
            )

            recommendations.extend(
                self._recommend_for_host(
                    hostname=hostname,
                    analysis=host["analysis"],
                    depth=host["depth"],
                    path=host["path"],
                )
            )

        if (
            entity_type == "host"
            and entity_id not in seen_hosts
        ):
            host_result = self.health.host(
                entity_id,
                limit=limit,
            )

            if host_result is not None:
                recommendations.extend(
                    self._recommend_for_host(
                        hostname=entity_id,
                        analysis=host_result[
                            "analysis"
                        ],
                        depth=0,
                        path=[],
                    )
                )

        recommendations.sort(
            key=lambda item: (
                self.SEVERITY_ORDER[
                    item["severity"]
                ],
                item["target"]["entity_id"],
                item["condition"],
            )
        )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "recommendation_count": len(
                recommendations
            ),
            "execution_performed": False,
            "recommendations": recommendations,
        }
