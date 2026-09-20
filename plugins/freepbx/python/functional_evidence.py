"""
FreePBX-specific functional evidence interpretation.

This module interprets raw observations collected from Asterisk.
Generic evidence validation, freshness, and service availability
remain owned by HIMP Core.
"""

import re

from himp.services.functional_evidence import (
    FunctionalEvidenceService,
)


class FreePBXFunctionalEvidence:

    SOURCE = "freepbx"

    AVAILABLE_STATE = "Registered"

    @classmethod
    def _registration_state(
        cls,
        registration_id,
        output,
    ):
        if not isinstance(registration_id, str):
            return None

        registration_id = registration_id.strip()

        if not registration_id:
            return None

        if not isinstance(output, str):
            return None

        pattern = re.compile(
            rf"^\s*"
            rf"{re.escape(registration_id)}"
            rf"/\S+\s+\S+\s+"
            rf"(?P<state>[A-Za-z]+)"
            rf"(?:\s+|$)",
            re.MULTILINE,
        )

        match = pattern.search(output)

        if match is None:
            return None

        return match.group("state")

    @classmethod
    def build(
        cls,
        observation,
        observed_at,
        entity_type,
        entity_id,
        now=None,
    ):
        if not isinstance(observation, dict):
            raise ValueError(
                "FreePBX observation must be a mapping"
            )

        registration = observation.get(
            "registration"
        )

        asterisk_cli = observation.get(
            "asterisk_cli"
        )

        if not isinstance(registration, dict):
            registration = {}

        if not isinstance(asterisk_cli, dict):
            asterisk_cli = {}

        registration_id = registration.get(
            "id",
            "",
        )

        registration_output = registration.get(
            "output",
            "",
        )

        registration_state = (
            cls._registration_state(
                registration_id,
                registration_output,
            )
        )

        asterisk_success = (
            asterisk_cli.get("successful")
            is True
        )

        registration_success = (
            registration.get("successful")
            is True
        )

        if (
            asterisk_success
            and registration_success
            and registration_state
            == cls.AVAILABLE_STATE
        ):
            state = (
                FunctionalEvidenceService.AVAILABLE
            )
            message = (
                "Configured PJSIP registration "
                "is registered."
            )
        else:
            state = (
                FunctionalEvidenceService.UNKNOWN
            )
            message = (
                "FreePBX functional state "
                "could not be established."
            )

        evidence = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "state": state,
            "evidence_type": observation.get(
                "evidence_type",
                "sip_registration",
            ),
            "source": cls.SOURCE,
            "observed_at": observed_at,
            "fresh_for_seconds": observation.get(
                "fresh_for_seconds",
            ),
            "message": message,
            "details": {
                "service_id": observation.get(
                    "service_id",
                ),
                "registration_id": (
                    registration_id
                ),
                "registration_state": (
                    registration_state
                ),
                "asterisk_cli_successful": (
                    asterisk_success
                ),
                "registration_probe_successful": (
                    registration_success
                ),
            },
        }

        return FunctionalEvidenceService.normalize(
            evidence,
            now=now,
        )
