"""Reduce Technitium probe output to allowlisted report fields."""

from datetime import datetime
from ipaddress import IPv4Address
import json
import re


def technitium_units(results):
    units = {}
    commands = {}
    errors = {}
    for result in results:
        unit = result["item"]
        values = dict(
            line.split("=", 1) for line in result.get("stdout", "").splitlines()
            if "=" in line
        )
        if values.get("LoadState") == "not-found":
            continue
        if result.get("rc") != 0 or values.get("LoadState") != "loaded":
            errors[unit] = (
                "no_permission" if re.search(
                    r"permission denied|access denied", result.get("stderr", ""), re.I
                ) else "unknown"
            )
            continue
        command = re.search(r"argv\[\]=([^;]+?)\s*;", values.get("ExecStart", ""))
        if not command or not re.search(r"(?:^|[ /])DnsServerApp\.dll(?:\s|$)", command[1]):
            errors[unit] = "unknown"
            continue
        canonical = values.get("Id")
        if canonical not in {"dns.service", "technitium.service"}:
            errors[unit] = "unknown"
            continue
        commands[canonical] = command[1].strip()
        units[canonical] = {
            "active": values.get("ActiveState") == "active",
            "enabled": values.get("UnitFileState") in {"enabled", "enabled-runtime"},
            "restarts": _count(values.get("NRestarts")),
            "pid": _count(values.get("MainPID")),
            "dynamic_user": values.get("DynamicUser") == "yes",
        }
    enabled_commands = [commands[name] for name, unit in units.items() if unit["enabled"]]
    return {
        "units": units,
        "errors": errors,
        "duplicate_enabled": len(enabled_commands) > len(set(enabled_commands)),
    }


def _count(value):
    return int(value) if value and re.fullmatch(r"[0-9]{1,20}", value) else None


def technitium_dns_result(result, name, expected):
    """Verify a direct A answer for the configured canary."""
    if result.get("skipped"):
        return "unknown"
    try:
        expected = str(IPv4Address(expected))
    except ValueError:
        return "unknown"

    output = result.get("stdout", "")
    if result.get("rc") == 124 or (
        result.get("rc") != 0
        and re.search(r"timed out|no servers could be reached", output, re.I)
    ):
        return "timeout"
    if result.get("rc") != 0:
        return "unknown"

    status = re.findall(
        r"^;; ->>HEADER<<- opcode: QUERY, status: ([A-Z]+),", output, re.M
    )
    if len(status) != 1:
        return "unknown"
    if status[0] in {"SERVFAIL", "REFUSED", "NXDOMAIN"}:
        return status[0].lower()
    if status[0] != "NOERROR":
        return "unknown"
    if any("tc" in flags.split() for flags in re.findall(r"^;; flags: ([^;]*);", output, re.M)):
        return "truncated"

    owner = name.rstrip(".").lower() + "."
    return "ok" if any(
        len(fields) == 5
        and fields[0].lower() == owner
        and fields[1].isdigit()
        and fields[2:4] == ["IN", "A"]
        and fields[4] == expected
        for fields in (line.split() for line in output.splitlines())
    ) else "unexpected_answer"


def technitium_restart_trend(evidence, previous_json, binding, address, user):
    """Compare a recent sample only when both executions bind the same host."""
    if not binding or binding.get("ip") != address or binding.get("user") != user:
        return {}
    identity = {key: binding.get(key) for key in ("host_id", "incarnation")}
    if any(value is None for value in identity.values()) or not evidence.get("boot_id"):
        return {}
    try:
        previous = json.loads(previous_json)
        matching = [
            row["report"] for row in previous["hosts"]
            if row.get("host_identity") == identity
        ]
        if len(matching) != 1:
            return {}
        old = matching[0]
        if old["boot_id"] != evidence["boot_id"]:
            return {}
        elapsed = (
            datetime.fromisoformat(evidence["observed_at"])
            - datetime.fromisoformat(old["observed_at"])
        ).total_seconds()
        if not 0 < elapsed <= 86400:
            return {}
        old_units = old["service_state"]["units"]
        deltas = {}
        for name, unit in evidence["service_state"]["units"].items():
            current = unit["restarts"]
            prior = old_units.get(name, {}).get("restarts")
            if type(current) is int and type(prior) is int and current >= prior:
                deltas[name] = {"delta": current - prior, "seconds": int(elapsed)}
        return deltas
    except (TypeError, AttributeError, KeyError, ValueError, RecursionError):
        return {}


class FilterModule:
    def filters(self):
        return {
            "technitium_units": technitium_units,
            "technitium_restart_trend": technitium_restart_trend,
            "technitium_dns_result": technitium_dns_result,
        }
