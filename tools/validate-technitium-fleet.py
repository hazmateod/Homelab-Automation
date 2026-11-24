#!/usr/bin/env python3
"""Compare an approved manifest with independently authenticated offline evidence."""

import argparse
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
import json
from pathlib import Path


TOPOLOGY = {
    **{("blackwatch", "pve01", ctid): "dns.service" for ctid in (310, 311)},
    **{("blackwatch", "pve02", ctid): "dns.service" for ctid in (312, 313)},
    **{("standalone-pve", "pve", ctid): "technitium.service" for ctid in (800, 801)},
    **{("standalone-prox", "prox", ctid): "technitium.service" for ctid in (600, 601)},
}
IDENTITY = (
    "hostname", "host_id", "incarnation", "ssh_fingerprint", "executable",
    "service", "canary", "answer",
)
DNS_CHECKS = ("local_udp", "local_tcp", "remote_udp", "remote_tcp")


def key(row):
    return row["scope"], row["node"], row["ctid"]


def validate(manifest, evidence, now):
    targets = manifest["targets"]
    expected = {key(row): row for row in targets}
    if manifest.get("approved") is not True or len(targets) != 8 or expected.keys() != TOPOLOGY.keys():
        raise ValueError("Expected an approved manifest with exactly the eight scoped targets.")
    if len({row["host_id"] for row in targets}) != 8 or len({row["hostname"] for row in targets}) != 8:
        raise ValueError("Manifest contains duplicate HIMP identities or hostnames.")
    rows = defaultdict(list)
    for row in evidence["targets"]:
        rows[key(row)].append(row)
    results = []
    for target, service in TOPOLOGY.items():
        approved = expected[target]
        if (
            any(not approved.get(field) for field in IDENTITY)
            or type(approved["incarnation"]) is not int
            or approved["incarnation"] < 1
            or approved["service"] != service
            or Path(approved["executable"]).name != "DnsServerApp.dll"
        ):
            raise ValueError("Manifest target has incomplete or invalid approval data.")
        IPv4Address(approved["answer"])
        matches = rows[target]
        status, reason = "UNKNOWN", "missing_evidence"
        if len(matches) > 1:
            status, reason = "FAIL", "ambiguous_scoped_binding"
        elif matches:
            observed = matches[0]
            unknown = [field for field in IDENTITY if observed.get(field) is None]
            mismatches = [field for field in IDENTITY if field not in unknown and observed[field] != approved[field]]
            if mismatches:
                status, reason = "FAIL", "mismatch:" + ",".join(mismatches)
            elif observed.get("collection_status") == "ssh_identity_failed":
                status, reason = "FAIL", "ssh_identity_failed"
            elif observed.get("collection_status") == "unreachable":
                reason = "unreachable"
            elif unknown or any(observed.get(flag) is not True for flag in
                                ("proxmox_authenticated", "ssh_verified", "active_inventory", "active_service")):
                reason = "unverified_identity_or_service"
            elif evidence.get("attempt_status") != "succeeded" or not evidence.get("attempt_id") or observed.get("attempt_id") != evidence["attempt_id"]:
                reason = "attempt_not_current"
            else:
                timestamp = observed.get("observed_at")
                age = now - datetime.fromisoformat(timestamp) if timestamp else None
                dns = observed.get("dns", {})
                if age is None or not timedelta(0) <= age <= timedelta(minutes=15):
                    reason = "stale_or_missing_observation"
                elif any(dns.get(check) not in ("ok", "unknown", None) for check in DNS_CHECKS):
                    status, reason = "FAIL", "dns_canary_failed"
                elif all(dns.get(check) == "ok" for check in DNS_CHECKS):
                    status, reason = "PASS", "verified"
                else:
                    reason = "dns_canary_evidence_missing"
        results.append(dict(scope=target[0], node=target[1], ctid=target[2],
                            status=status, reason=reason))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        results = validate(json.loads(args.manifest.read_text()),
                           json.loads(args.evidence.read_text()), datetime.now(UTC))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        results = [{"status": "UNKNOWN", "reason": "invalid_manifest_or_evidence"}]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for row in results:
            label = "/".join(str(row.get(field, "?")) for field in ("scope", "node", "ctid"))
            print(f"{label}: {row['status']} ({row['reason']})")
    return int(any(row["status"] != "PASS" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
