"""Project current Technitium evidence against authoritative HIMP identities."""

from collections import Counter

from himp.health.models import HealthCheckResult, HealthStatus, HostHealthResult


def project_fleet(report, inventory, disabled, freshness, report_bindings):
    members = {row["hostname"]: row for row in inventory if row["group_name"] == "technitium"}
    evidence = report.metadata.data
    rows = evidence.get("hosts", [])
    counts = Counter(row.get("hostname") for row in rows)
    observations = {host.hostname: host for host in report.hosts}
    raw = {row["hostname"]: row for row in rows if "hostname" in row}
    hosts = []
    public = []
    states = Counter()

    for name in sorted(members.keys() | raw.keys()):
        member = members.get(name)
        host = observations.get(name)
        identity = host.host_identity if host is not None else None
        expected = {
            "host_id": member["host_id"], "incarnation": member["current_incarnation"],
        } if member else None
        if name in disabled:
            state = "disabled"
        elif member is None and name in report_bindings and report_bindings[name] is None:
            state = "retired"
        elif not member or member["endpoint_review_required"]:
            state = "unverified"
        elif freshness != "current" or host is None:
            state = "unknown"
        elif counts[name] != 1 or identity != expected or type(identity.get("incarnation")) is not int:
            state = "unverified"
        else:
            status = host.results[0].status
            state = {HealthStatus.PASS: "healthy", HealthStatus.UNKNOWN: "unknown"}.get(status, "unhealthy")
        states[state] += 1
        if state in {"healthy", "unhealthy"}:
            hosts.append(host)
            public.append(raw[name])
        else:
            result = HealthCheckResult(
                plugin="technitium", check="health", status=HealthStatus.UNKNOWN,
                message=state, details={"earned": 0, "possible": 10},
            )
            hosts.append(HostHealthResult(
                hostname=name, results=[result],
                host_identity=expected if state == "unknown" else None,
            ))
            public.append({"hostname": name, "health": {"status": "UNKNOWN"},
                           "report": {"collection_status": state}})

    healthy = states["healthy"]
    status = (
        HealthStatus.PASS if hosts and healthy == len(hosts)
        else HealthStatus.WARNING if healthy
        else HealthStatus.FAIL if states["unhealthy"]
        else HealthStatus.UNKNOWN
    )
    return report.model_copy(update={
        "hosts": hosts,
        "summary": report.summary.model_copy(update={
            "status": status, "score": healthy * 10, "possible": len(hosts) * 10,
        }),
        "metadata": report.metadata.model_copy(update={
            "data": {
                **evidence, "hosts": public, "fleet_membership": dict(states),
                "last_observation_status": report.summary.status.value,
            },
        }),
    })
