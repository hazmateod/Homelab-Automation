"""
Remediation Verification Service.

Performs a fresh post-remediation health check using the existing
HostHealthService. This service owns verification only; remediation
policy and automation execution remain delegated to their existing
services.
"""

from himp.services.host_health import (
    HostHealthService,
)


class RemediationVerificationService:
    """
    Verifies the infrastructure condition after remediation execution.
    """

    def __init__(
        self,
        health=None,
    ):
        self.health = (
            health
            if health is not None
            else HostHealthService()
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

    def verify(
        self,
        proposal,
        remediation,
    ):
        if remediation.get(
            "decision"
        ) != "ALLOW":
            return {
                "status": "NOT_EXECUTED",
                "success": False,
            }

        hostname = self._hostname_from_proposal(
            proposal
        )

        if not hostname:
            return {
                "status": "NOT_SUPPORTED",
                "success": False,
            }

        health = self.health.check_host(
            hostname
        )

        results = health.get(
            "results",
            [],
        )

        status = (
            results[0].get("status")
            if results
            else "UNKNOWN"
        )

        if status == "PASS":
            return {
                "status": "VERIFIED",
                "success": True,
                "hostname": hostname,
                "health": health,
            }

        return {
            "status": "FAILED",
            "success": False,
            "hostname": hostname,
            "health": health,
        }
