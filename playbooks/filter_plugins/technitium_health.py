"""Reduce Technitium probe output to allowlisted report fields."""

from datetime import datetime
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


def technitium_dns_result(result, expected):
    if result.get("skipped"):
        return "unknown"
    output = result.get("stdout", "")
    status = re.search(r"status: ([A-Z]+),", output)
    if status and status[1] in {"SERVFAIL", "REFUSED", "NXDOMAIN"}:
        return status[1].lower()
    if result.get("rc") != 0:
        if re.search(r"timed out|no servers could be reached", output, re.I):
            return "timeout"
        return "unknown"
    if not status or status[1] != "NOERROR":
        return "unknown"
    return "ok" if any(
        len(fields) == 5 and fields[2:4] == ["IN", "A"] and fields[4] == expected
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


def technitium_capacity_report(disk, directories, ages, job, observed_at):
    """Keep capacity and eligibility facts without filenames or log contents."""
    report = {
        "root": {},
        "query_log_bytes": None,
        "local_backup_bytes": None,
        "oldest_log_age_days": None,
        "eligible_logs": None,
        "retention_job_executable": None,
        "last_successful_retention": None,
        "pbs_backup": "unknown",
        "restore_verification": "unknown",
    }
    if disk.get("rc") == 0:
        rows = disk.get("stdout", "").splitlines()
        fields = rows[-1].split() if len(rows) == 2 else []
        if len(fields) == 6:
            size, available, percent, inodes, free_inodes, inode_percent = (
                _count(value.removesuffix("%")) for value in fields
            )
            report["root"] = {
                "total_bytes": size * 1024 if size is not None else None,
                "available_bytes": available * 1024 if available is not None else None,
                "used_percent": percent,
                "total_inodes": inodes,
                "available_inodes": free_inodes,
                "used_inode_percent": inode_percent,
                "severity": _capacity_severity(percent),
            }
    labels = {
        "/var/log/technitium/dns": "query_log_bytes",
        "/root/backups": "local_backup_bytes",
    }
    for directory in directories:
        label = labels.get(directory.get("item"))
        size, separator, _ = directory.get("stdout", "").partition("\t")
        if label and directory.get("rc") == 0 and separator:
            report[label] = _count(size)
    if ages.get("rc") == 0:
        timestamps = ages.get("stdout", "").splitlines()
        if all(re.fullmatch(r"[0-9]{1,20}(?:\.[0-9]{1,20})?", value) for value in timestamps):
            observation = datetime.fromisoformat(observed_at).timestamp()
            oldest_days = [
                max(0, int((observation - float(value)) // 86400))
                for value in timestamps
            ]
            report["oldest_log_age_days"] = max(oldest_days, default=None)
            report["eligible_logs"] = sum(days >= 90 for days in oldest_days)
    if "exists" in job:
        report["retention_job_executable"] = bool(job.get("isreg") and job.get("executable"))
    return report


def _capacity_severity(percent):
    if percent is None:
        return "unknown"
    if percent >= 90:
        return "critical"
    if percent >= 80:
        return "warning"
    return "healthy"


class FilterModule:
    def filters(self):
        return {
            "technitium_units": technitium_units,
            "technitium_restart_trend": technitium_restart_trend,
            "technitium_capacity_report": technitium_capacity_report,
            "technitium_dns_result": technitium_dns_result,
        }
