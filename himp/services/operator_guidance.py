"""
Operator Guidance Service.

Provides reviewed, deterministic operator guidance for HIMP
operational conditions.

Guidance is informational only. This service does not execute
remediation or modify infrastructure.
"""

from pathlib import Path

import yaml


class OperatorGuidanceService:
    """
    Loads and validates the Git-managed operator guidance catalog.
    """

    REQUIRED_FIELDS = (
        "category",
        "severity",
        "title",
        "urgency",
        "summary",
        "meaning",
        "affects",
        "resolved_when",
        "safe_actions",
        "can_wait",
        "do_not",
        "escalation",
        "detail_href",
    )

    URGENCY_LEVELS = frozenset(
        {
            "NO_ACTION_NEEDED",
            "CHECK_WHEN_CONVENIENT",
            "ACTION_RECOMMENDED",
            "GET_TECHNICAL_HELP",
        }
    )

    SEVERITIES = frozenset(
        {
            "PASS",
            "WARNING",
            "FAIL",
        }
    )

    def __init__(
        self,
        config_path=None,
    ):
        self.config_path = Path(
            config_path
            or "config/operator_guidance.yml"
        )

    @staticmethod
    def _required_text(
        entry_id,
        field,
        value,
    ):
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"Guidance entry {entry_id} field "
                f"{field} must not be empty"
            )

        return value.strip()

    def _normalize_entry(
        self,
        entry_id,
        item,
    ):
        if not isinstance(item, dict):
            raise ValueError(
                f"Guidance entry {entry_id} must be a mapping"
            )

        missing = [
            field
            for field in self.REQUIRED_FIELDS
            if field not in item
        ]

        if missing:
            raise ValueError(
                f"Guidance entry {entry_id} missing fields: "
                + ", ".join(missing)
            )

        normalized = {
            field: self._required_text(
                entry_id,
                field,
                item[field],
            )
            for field in self.REQUIRED_FIELDS
            if field not in {
                "safe_actions",
                "do_not",
            }
        }

        severity = normalized["severity"].upper()

        if severity not in self.SEVERITIES:
            raise ValueError(
                f"Guidance entry {entry_id} has unsupported "
                f"severity: {severity}"
            )

        normalized["severity"] = severity

        urgency = normalized["urgency"].upper()

        if urgency not in self.URGENCY_LEVELS:
            raise ValueError(
                f"Guidance entry {entry_id} has unsupported "
                f"urgency: {urgency}"
            )

        normalized["urgency"] = urgency

        for field in (
            "safe_actions",
            "do_not",
        ):
            values = item[field]

            if (
                not isinstance(values, list)
                or not values
            ):
                raise ValueError(
                    f"Guidance entry {entry_id} field "
                    f"{field} must be a non-empty list"
                )

            normalized[field] = [
                self._required_text(
                    entry_id,
                    field,
                    value,
                )
                for value in values
            ]

        normalized["id"] = entry_id

        return normalized

    def load(self):
        if not self.config_path.exists():
            raise FileNotFoundError(
                self.config_path
            )

        with self.config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file) or {}

        if not isinstance(data, dict):
            raise ValueError(
                "Operator guidance configuration must be a mapping"
            )

        guidance = data.get(
            "guidance",
            {},
        )

        if not isinstance(guidance, dict):
            raise ValueError(
                "guidance must be a mapping"
            )

        result = {}

        for entry_id, item in guidance.items():
            if (
                not isinstance(entry_id, str)
                or not entry_id.strip()
            ):
                raise ValueError(
                    "Guidance entry ID must not be empty"
                )

            normalized_id = entry_id.strip()

            if normalized_id in result:
                raise ValueError(
                    "Duplicate guidance entry: "
                    f"{normalized_id}"
                )

            result[normalized_id] = (
                self._normalize_entry(
                    normalized_id,
                    item,
                )
            )

        return result

    def get(
        self,
        entry_id,
    ):
        return self.load().get(
            entry_id
        )

    HOST_GUIDANCE_DOMAINS = {
        "dns": frozenset(
            {
                "pihole",
                "technitium",
                "unbound",
            }
        ),
        "backup": frozenset(
            {
                "backup",
            }
        ),
        "virtualization": frozenset(
            {
                "proxmox",
            }
        ),
        "media": frozenset(
            {
                "media",
            }
        ),
        "vpn": frozenset(
            {
                "vpn",
            }
        ),
        "telephony": frozenset(
            {
                "telephony",
            }
        ),
    }

    @classmethod
    def _host_guidance_domain(
        cls,
        attention,
    ):
        affected_hosts = attention.get(
            "affected_hosts",
            [],
        )

        if (
            not isinstance(
                affected_hosts,
                list,
            )
            or not affected_hosts
            or not all(
                isinstance(host, dict)
                and isinstance(
                    host.get("group"),
                    str,
                )
                and host["group"].strip()
                for host in affected_hosts
            )
        ):
            return None

        affected_groups = {
            host["group"].strip()
            for host in affected_hosts
        }

        for domain, groups in (
            cls.HOST_GUIDANCE_DOMAINS.items()
        ):
            if affected_groups.issubset(
                groups
            ):
                return domain

        return None

    def for_attention(
        self,
        attention,
    ):
        category = attention.get(
            "category"
        )

        severity = attention.get(
            "severity"
        )

        if category == "Host Connectivity":
            domain = self._host_guidance_domain(
                attention
            )

            if domain is not None:
                guidance_id = {
                    (
                        "dns",
                        "FAIL",
                    ): "dns_connectivity_failed",
                    (
                        "dns",
                        "WARNING",
                    ): "dns_connectivity_warning",
                    (
                        "backup",
                        "FAIL",
                    ): "backup_connectivity_failed",
                    (
                        "backup",
                        "WARNING",
                    ): "backup_connectivity_warning",
                    (
                        "virtualization",
                        "FAIL",
                    ): "virtualization_connectivity_failed",
                    (
                        "virtualization",
                        "WARNING",
                    ): "virtualization_connectivity_warning",
                    (
                        "media",
                        "FAIL",
                    ): "media_connectivity_failed",
                    (
                        "media",
                        "WARNING",
                    ): "media_connectivity_warning",
                    (
                        "vpn",
                        "FAIL",
                    ): "vpn_connectivity_failed",
                    (
                        "vpn",
                        "WARNING",
                    ): "vpn_connectivity_warning",
                    (
                        "telephony",
                        "FAIL",
                    ): "telephony_connectivity_failed",
                    (
                        "telephony",
                        "WARNING",
                    ): "telephony_connectivity_warning",
                }.get(
                    (
                        domain,
                        severity,
                    )
                )

                if guidance_id is not None:
                    return self.get(
                        guidance_id
                    )

        guidance_id = {
            (
                "Host Connectivity",
                "FAIL",
            ): "host_connectivity_failed",
            (
                "Host Connectivity",
                "WARNING",
            ): "host_connectivity_warning",
            (
                "Workflow",
                "FAIL",
            ): "workflow_failed",
            (
                "Automation",
                "FAIL",
            ): "automation_failed",
            (
                "Remediation",
                "FAIL",
            ): "remediation_execution_failed",
            (
                "Remediation",
                "WARNING",
            ): "remediation_confirmation_required",
        }.get(
            (
                category,
                severity,
            )
        )

        if guidance_id is None:
            return None

        return self.get(
            guidance_id
        )


    def safe_for_attention(
        self,
        attention,
    ):
        """
        Return optional presentation guidance without allowing a
        catalog problem to break the owning operations page.
        """

        try:
            return self.for_attention(
                attention
            )
        except (
            OSError,
            UnicodeError,
            yaml.YAMLError,
            ValueError,
        ):
            return None
