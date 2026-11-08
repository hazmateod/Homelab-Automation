"""Lifecycle coordination for durable maintenance progress."""

import logging

from himp.services.automation_progress import (
    AutomationProgressTracker,
)


logger = logging.getLogger("himp.automation.progress")


class AutomationProgressLifecycle:
    """Manage progress for one automation execution attempt."""

    def __init__(
        self,
        repository,
        task_id,
        attempt,
        execution_token,
    ):
        if not execution_token:
            raise ValueError("Execution token is required")

        self.repository = repository
        self.task_id = task_id
        self.attempt = attempt
        self.execution_token = execution_token
        self.run_id = None
        self.tracker = None

    def start(self, eligible_hosts, excluded_hosts=None):
        if self.run_id is not None:
            raise ValueError("Progress attempt already started")

        self.run_id = self.repository.start(
            self.task_id,
            attempt=self.attempt,
            hosts=list(eligible_hosts),
            execution_token=self.execution_token,
        )

        self.tracker = AutomationProgressTracker(
            self.repository,
            self.run_id,
            self.execution_token,
        )

        return self.run_id

    def handle_event(self, event):
        if self.tracker is None:
            raise ValueError("Progress attempt has not started")

        return self.tracker.handle_event(event)

    def finalize(self, success, execution_id=None):
        if self.run_id is None:
            raise ValueError("Progress attempt has not started")

        return self.repository.update(
            self.run_id,
            status="succeeded" if success else "failed",
            completed_execution_id=execution_id,
            execution_token=self.execution_token,
        )

    def interrupt(self):
        if self.run_id is None:
            raise ValueError("Progress attempt has not started")

        return self.repository.interrupt(
            self.run_id,
            execution_token=self.execution_token,
        )


    def finalize_safely(self, success, execution_id=None):
        """Finalize progress without changing execution outcome."""
        if self.run_id is None:
            return False

        try:
            self.finalize(
                success=success,
                execution_id=execution_id,
            )
            return True

        except Exception:
            logger.exception(
                "Automation progress finalization failed: "
                "task=%s run=%s",
                self.task_id,
                self.run_id,
            )
            return False


    def start_safely(self, eligible_hosts, excluded_hosts=None):
        """Start progress without affecting maintenance execution."""
        try:
            return self.start(
                eligible_hosts,
                excluded_hosts,
            )

        except Exception:
            logger.exception(
                "Automation progress initialization failed: "
                "task=%s attempt=%s",
                self.task_id,
                self.attempt,
            )
            self.tracker = None
            return None

    def handle_event_safely(self, event):
        """Ignore progress errors without interrupting Ansible."""
        if self.tracker is None:
            return False

        try:
            self.handle_event(event)
            return True

        except Exception:
            logger.exception(
                "Automation progress event persistence failed: "
                "task=%s run=%s",
                self.task_id,
                self.run_id,
            )
            self.tracker = None
            return False
