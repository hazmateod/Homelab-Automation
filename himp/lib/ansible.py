"""
Shared Ansible helper functions.
"""

import subprocess
import time
from dataclasses import dataclass

from himp.config import config


@dataclass(frozen=True)
class AnsiblePlaybookResult:
    """Result returned by an Ansible playbook execution."""

    success: bool
    return_code: int
    elapsed: float
    stdout: str
    stderr: str


class AnsiblePlaybookTimeoutError(TimeoutError):
    """Raised when an Ansible playbook exceeds its timeout."""


def run_playbook(
    playbook,
    limit=None,
    timeout=None,
):
    cmd = [
        "ansible-playbook",
        "-i",
        config.inventory,
        playbook,
    ]

    if limit:
        cmd.extend([
            "--limit",
            limit,
        ])

    start = time.perf_counter()

    try:
        result = subprocess.run(
            cmd,
            check=False,
            timeout=timeout,
            capture_output=True,
            text=True,
        )

    except subprocess.TimeoutExpired as error:
        raise AnsiblePlaybookTimeoutError(
            "Ansible playbook timed out"
        ) from error

    elapsed = time.perf_counter() - start

    return AnsiblePlaybookResult(
        success=result.returncode == 0,
        return_code=result.returncode,
        elapsed=elapsed,
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )



def run_playbook_streaming(
    playbook,
    limit=None,
    timeout=None,
    on_output=None,
    on_event=None,
    structured_events=False,
):
    """Run Ansible with incremental stdout callbacks."""
    import json
    import os
    import queue
    import signal
    import threading
    from pathlib import Path

    from himp.lib.ansible_events import (
        MAX_EVENT_BYTES,
        validate_ansible_event,
    )

    cmd = [
        "ansible-playbook",
        "-i",
        config.inventory,
        playbook,
    ]

    if limit:
        cmd.extend(["--limit", limit])

    started = time.monotonic()
    deadline = (
        started + timeout
        if timeout is not None
        else None
    )

    events = queue.Queue()
    stdout_lines = []
    stderr_lines = []

    environment = os.environ.copy()

    if structured_events:
        callback_directory = (
            Path(__file__).resolve().parents[1]
            / "ansible_plugins"
            / "callback"
        )

        environment["ANSIBLE_CALLBACK_PLUGINS"] = (
            str(callback_directory)
        )
        environment["ANSIBLE_CALLBACKS_ENABLED"] = (
            "himp_events"
        )

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        start_new_session=True,
        env=environment,
    )

    def terminate_group():
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def reader(stream, destination, emit):
        try:
            for line in stream:
                destination.append(line)

                if emit:
                    events.put(("stdout", line.rstrip("\r\n")))
        except Exception as error:
            events.put(("reader_error", error))
        finally:
            stream.close()
            events.put(("reader_done", None))

    threads = [
        threading.Thread(
            target=reader,
            args=(process.stdout, stdout_lines, True),
            daemon=True,
        ),
        threading.Thread(
            target=reader,
            args=(process.stderr, stderr_lines, False),
            daemon=True,
        ),
    ]

    for thread in threads:
        thread.start()

    completed_readers = 0

    try:
        while completed_readers < 2:
            remaining = (
                None
                if deadline is None
                else deadline - time.monotonic()
            )

            if remaining is not None and remaining <= 0:
                raise AnsiblePlaybookTimeoutError(
                    "Ansible playbook timed out"
                )

            try:
                kind, value = events.get(
                    timeout=(
                        0.1
                        if remaining is None
                        else min(0.1, remaining)
                    )
                )
            except queue.Empty:
                continue

            if kind == "reader_done":
                completed_readers += 1
            elif kind == "reader_error":
                raise RuntimeError(
                    "Ansible output reader failed"
                ) from value
            elif kind == "stdout":
                if structured_events and value.startswith(
                    "HIMP_EVENT:"
                ):
                    raw_event = value[len("HIMP_EVENT:"):]

                    if len(raw_event.encode("utf-8")) > MAX_EVENT_BYTES:
                        raise RuntimeError(
                            "HIMP event exceeds size limit"
                        )

                    try:
                        payload = json.loads(raw_event)
                    except (ValueError, TypeError) as error:
                        raise RuntimeError(
                            "Invalid HIMP structured event"
                        ) from error

                    if not isinstance(payload, dict):
                        raise RuntimeError(
                            "HIMP event must be a JSON object"
                        )

                    if not isinstance(
                        payload.get("event"),
                        str,
                    ):
                        raise RuntimeError(
                            "HIMP event missing event type"
                        )

                    try:
                        validated = validate_ansible_event(
                            payload
                        )
                    except ValueError as error:
                        raise RuntimeError(
                            "Rejected HIMP structured event"
                        ) from error

                    if on_event is not None:
                        on_event(validated)

                elif on_output is not None:
                    on_output(value)

        remaining = (
            None
            if deadline is None
            else max(0, deadline - time.monotonic())
        )

        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as error:
            raise AnsiblePlaybookTimeoutError(
                "Ansible playbook timed out"
            ) from error

    except BaseException:
        terminate_group()
        raise

    finally:
        for thread in threads:
            thread.join(timeout=1)

    elapsed = time.monotonic() - started

    return AnsiblePlaybookResult(
        success=process.returncode == 0,
        return_code=process.returncode,
        elapsed=elapsed,
        stdout="".join(stdout_lines).strip(),
        stderr="".join(stderr_lines).strip(),
    )
