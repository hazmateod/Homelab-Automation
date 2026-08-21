"""
Remediation Verification Service.

Performs a fresh post-remediation host-health check and evaluates whether
the condition that justified remediation has actually cleared.

Execution success and verification success are deliberately separate.
A successful automation command does not by itself prove remediation
success.
"""

from himp.services.health_analysis import (
    HealthAnalysisService,
)
from himp.services.host_health import (
    HostHealthService,
)


class RemediationVerificationService:
    """
    Verify post-remediation infrastructure state.
    """

    SUPPORTED_CONDITIONS = {
        "HOST_UNHEALTHY",
        "HOST_FLAPPING",
    }

    def __init__(
        self,
        health=None,
        analysis=None,
    ):
        self.health = (
            health
            if health is not None
            else HostHealthService()
        )

        self.analysis = (
            analysis
            if analysis is not None
            else HealthAnalysisService()
        )

    @staticmethod
    def _hostname_from_proposal(
        proposal,
    ):
        evidence = proposal.get(
            "evidence",
            {},
        )

        if (
            evidence.get("target_type") == "host"
            and evidence.get("target_id")
        ):
            return evidence["target_id"]

        drift = evidence.get(
            "drift",
            [],
        )

        for item in drift:
            hostname = item.get(
                "hostname"
            )

            if hostname:
                return hostname

        return None

    @staticmethod
    def _condition_from_proposal(
        proposal,
    ):
        condition = proposal.get(
            "condition"
        )

        if condition:
            return condition

        return proposal.get(
            "evidence",
            {},
        ).get(
            "condition"
        )

    @staticmethod
    def _fresh_status(
        health,
    ):
        results = health.get(
            "results",
            [],
        )

        if not results:
            return "UNKNOWN"

        return (
            results[0].get(
                "status"
            )
            or "UNKNOWN"
        )

    @staticmethod
    def _result(
        *,
        status,
        success,
        hostname=None,
        condition=None,
        health=None,
        analysis=None,
        reason=None,
    ):
        evidence = {}

        if health is not None:
            evidence["fresh_health"] = (
                health
            )

        if analysis is not None:
            evidence["post_analysis"] = (
                analysis
            )

        return {
            "status": status,
            "success": bool(success),
            "hostname": hostname,
            "condition": condition,
            "reason": reason,
            "evidence": evidence,
        }

    def verify(
        self,
        proposal,
        remediation,
    ):
        if remediation.get(
            "decision"
        ) != "ALLOW":
            return self._result(
                status="NOT_EXECUTED",
                success=False,
                condition=(
                    self._condition_from_proposal(
                        proposal
                    )
                ),
                reason=(
                    "Remediation was not executed."
                ),
            )

        execution = remediation.get(
            "execution"
        ) or {}

        if execution.get(
            "success"
        ) is False:
            return self._result(
                status="EXECUTION_FAILED",
                success=False,
                condition=(
                    self._condition_from_proposal(
                        proposal
                    )
                ),
                reason=(
                    "Automation execution failed before "
                    "verification could confirm recovery."
                ),
            )

        hostname = (
            self._hostname_from_proposal(
                proposal
            )
        )

        condition = (
            self._condition_from_proposal(
                proposal
            )
        )

        if not hostname:
            return self._result(
                status="NOT_SUPPORTED",
                success=False,
                condition=condition,
                reason=(
                    "No host target could be derived "
                    "from the remediation proposal."
                ),
            )

        fresh_health = (
            self.health.check_host(
                hostname
            )
        )

        fresh_status = (
            self._fresh_status(
                fresh_health
            )
        )

        # Existing immediate-remediation proposals predate
        # condition-aware recommendation snapshots. Preserve
        # deterministic host-health verification for those
        # proposals while making scheduled recommendation
        # verification condition-aware.
        if condition is None:
            if fresh_status == "PASS":
                return self._result(
                    status="VERIFIED",
                    success=True,
                    hostname=hostname,
                    health=fresh_health,
                    reason=(
                        "Fresh host health returned PASS."
                    ),
                )

            return self._result(
                status="NOT_VERIFIED",
                success=False,
                hostname=hostname,
                health=fresh_health,
                reason=(
                    "Fresh host health did not return PASS."
                ),
            )

        if (
            condition
            not in self.SUPPORTED_CONDITIONS
        ):
            return self._result(
                status="NOT_SUPPORTED",
                success=False,
                hostname=hostname,
                condition=condition,
                health=fresh_health,
                reason=(
                    "Verification does not support "
                    f"condition {condition}."
                ),
            )

        if condition == "HOST_UNHEALTHY":
            if fresh_status == "PASS":
                return self._result(
                    status="VERIFIED",
                    success=True,
                    hostname=hostname,
                    condition=condition,
                    health=fresh_health,
                    reason=(
                        "HOST_UNHEALTHY cleared: fresh "
                        "host health returned PASS."
                    ),
                )

            return self._result(
                status="NOT_VERIFIED",
                success=False,
                hostname=hostname,
                condition=condition,
                health=fresh_health,
                reason=(
                    "HOST_UNHEALTHY remains present: "
                    "fresh host health is not PASS."
                ),
            )

        # HOST_FLAPPING requires both a fresh successful
        # observation and re-analysis of persisted history.
        analysis_result = (
            self.analysis.host(
                hostname,
                limit=100,
            )
        )

        if analysis_result is None:
            return self._result(
                status="NOT_SUPPORTED",
                success=False,
                hostname=hostname,
                condition=condition,
                health=fresh_health,
                reason=(
                    "HOST_FLAPPING cannot be confirmed "
                    "because no post-remediation health "
                    "history is available."
                ),
            )

        analysis = analysis_result[
            "analysis"
        ]

        if (
            fresh_status == "PASS"
            and not analysis["is_flapping"]
        ):
            return self._result(
                status="VERIFIED",
                success=True,
                hostname=hostname,
                condition=condition,
                health=fresh_health,
                analysis=analysis_result,
                reason=(
                    "HOST_FLAPPING cleared: fresh health "
                    "returned PASS and bounded historical "
                    "analysis no longer reports flapping."
                ),
            )

        return self._result(
            status="NOT_VERIFIED",
            success=False,
            hostname=hostname,
            condition=condition,
            health=fresh_health,
            analysis=analysis_result,
            reason=(
                "HOST_FLAPPING remains unresolved: "
                "fresh health is not PASS or bounded "
                "historical analysis still reports "
                "flapping."
            ),
        )
