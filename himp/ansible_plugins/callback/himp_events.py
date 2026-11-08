"""
HIMP structured Ansible execution events.

Emits sanitized JSON Lines events for live maintenance monitoring.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ansible.plugins.callback import CallbackBase

# Ansible loads callback plugins outside the normal HIMP
# package import context. Resolve the project root explicitly.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
project_root_string = str(PROJECT_ROOT)

if project_root_string not in sys.path:
    sys.path.insert(0, project_root_string)

from himp.lib.ansible_sanitize import sanitize_event


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "notification"
    CALLBACK_NAME = "himp_events"
    CALLBACK_NEEDS_WHITELIST = True

    def _emit(self, event, **fields):
        payload = {
            "event": event,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            **fields,
        }

        # Fail closed: never emit an unsanitized event.
        safe_payload = sanitize_event(payload)

        serialized = json.dumps(
            safe_payload,
            separators=(",", ":"),
            sort_keys=True,
        )

        self._display.display(
            "HIMP_EVENT:" + serialized
        )

    def v2_playbook_on_play_start(self, play):
        self._emit(
            "play_started",
            play=play.get_name(),
        )

    def v2_playbook_on_task_start(
        self,
        task,
        is_conditional,
    ):
        self._emit(
            "task_started",
            task=task.get_name(),
        )

    def _host_result(self, event, result):
        host = result._host.get_name()
        task = result._task.get_name()
        data = result._result

        fields = {
            "host": host,
            "task": task,
            "changed": bool(data.get("changed", False)),
        }

        if event in ("failed", "unreachable"):
            fields["error"] = str(
                data.get("msg", event)
            )[:2000]

        self._emit(
            event,
            **fields,
        )

    def v2_runner_on_ok(self, result):
        self._host_result("task_ok", result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._host_result("failed", result)

    def v2_runner_on_unreachable(self, result):
        self._host_result("unreachable", result)

    def v2_runner_on_skipped(self, result):
        self._host_result("skipped", result)

    def v2_playbook_on_stats(self, stats):
        summary = {}

        for host in sorted(stats.processed):
            values = stats.summarize(host)

            summary[host] = {
                "ok": values.get("ok", 0),
                "changed": values.get("changed", 0),
                "failed": values.get("failures", 0),
                "unreachable": values.get("unreachable", 0),
                "skipped": values.get("skipped", 0),
            }

        self._emit(
            "playbook_finished",
            hosts=summary,
        )
