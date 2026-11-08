"""
Parse Ansible PLAY RECAP into structured host results.

This parser does not execute Ansible or modify infrastructure.
"""

import re


RECAP_HEADER = re.compile(
    r"^\s*PLAY RECAP\s*$"
)

HOST_LINE = re.compile(
    r"^\s*(?P<host>\S+)\s*:\s*"
    r"(?P<counts>.*)$"
)

COUNT = re.compile(
    r"\b(ok|changed|unreachable|failed|skipped|"
    r"rescued|ignored)=(\d+)\b"
)

FIELDS = (
    "ok",
    "changed",
    "unreachable",
    "failed",
    "skipped",
    "rescued",
    "ignored",
)


def parse_play_recap(output):
    """Return structured results indexed by hostname."""

    if not output:
        return {}

    hosts = {}
    in_recap = False

    for line in output.splitlines():
        if RECAP_HEADER.match(line):
            in_recap = True
            hosts = {}
            continue

        if not in_recap:
            continue

        match = HOST_LINE.match(line)

        if not match:
            continue

        host = match.group("host")
        counts_text = match.group("counts")

        parsed = {
            key: int(value)
            for key, value in COUNT.findall(counts_text)
        }

        if not parsed or "ok" not in parsed:
            continue

        counts = {
            field: parsed.get(field, 0)
            for field in FIELDS
        }

        if counts["unreachable"] > 0:
            status = "unreachable"
        elif counts["failed"] > 0:
            status = "failed"
        elif (
            counts["ok"] == 0
            and counts["changed"] == 0
            and counts["skipped"] > 0
        ):
            status = "skipped"
        else:
            status = "succeeded"

        hosts[host] = {
            "host": host,
            "status": status,
            **counts,
        }

    return hosts
