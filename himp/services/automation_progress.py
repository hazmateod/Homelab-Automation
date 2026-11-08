"""Translate validated Ansible events into durable host progress."""

from himp.lib.ansible_events import validate_ansible_event


class AutomationProgressTracker:
    """Maintain per-host progress for one execution attempt."""

    def __init__(self, repository, run_id, execution_token):
        if not isinstance(execution_token, str) or not execution_token:
            raise ValueError("Execution token is required")

        self.repository = repository
        self.run_id = run_id
        self.execution_token = execution_token

    def handle_event(self, event):
        event = validate_ansible_event(event)

        current = self.repository.get(self.run_id)

        if current is None:
            raise ValueError("Unknown automation progress run")

        if current["execution_token"] != self.execution_token:
            raise ValueError("Execution token ownership mismatch")

        if current["status"] != "running":
            raise ValueError("Execution progress is already finalized")

        hosts = dict(current["host_results"])
        event_type = event["event"]

        if event_type == "playbook_finished":
            for host, counters in event["hosts"].items():
                if counters["unreachable"] > 0:
                    status = "unreachable"
                elif counters["failed"] > 0:
                    status = "failed"
                else:
                    status = "succeeded"

                hosts[host] = {
                    "host": host,
                    "status": status,
                    "ok": counters["ok"],
                    "changed": counters["changed"],
                    "failed": counters["failed"],
                    "unreachable": counters["unreachable"],
                    "skipped": counters["skipped"],
                }

        elif event_type in {
            "task_ok",
            "failed",
            "unreachable",
            "skipped",
        }:
            host = event["host"]

            previous = hosts.get(
                host,
                {"host": host, "status": "pending"},
            )

            # Task failures can be ignored or rescued.
            # Do not declare final host failure before recap.
            if previous["status"] not in {
                "failed",
                "unreachable",
                "succeeded",
            }:
                hosts[host] = {
                    **previous,
                    "status": "running",
                    "last_task": event["task"],
                    "last_event": event_type,
                    "updated_at": event["timestamp"],
                }

        else:
            return current

        return self.repository.update(
            self.run_id,
            host_results=hosts,
            execution_token=self.execution_token,
        )
