"""
Remediation Operations Service.

Provides the operational configuration used to trigger
scheduled remediation without owning scheduling or execution.
"""

from himp.database.remediation_operations import (
    RemediationOperationsRepository,
)


class RemediationOperationsService:
    """
    Manages scheduled remediation operational configuration.
    """

    def __init__(
        self,
        repository=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else RemediationOperationsRepository()
        )

    def get(self):
        return self.repository.get()

    def configure(
        self,
        enabled,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
    ):
        if not source_type:
            raise ValueError(
                "source_type is required"
            )

        if not source_id:
            raise ValueError(
                "source_id is required"
            )

        if change_limit < 1:
            raise ValueError(
                "change_limit must be at least 1"
            )

        return self.repository.save(
            enabled=enabled,
            source_type=source_type,
            source_id=source_id,
            baseline=baseline,
            change_limit=change_limit,
        )
