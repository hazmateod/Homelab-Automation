import json
from datetime import UTC, datetime
from pathlib import Path
import runpy
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "validate-technitium-fleet.py"
MODULE = runpy.run_path(str(SCRIPT))


@pytest.mark.parametrize(("change", "status"), [
    (None, "PASS"), ("scope", "UNKNOWN"), ("incarnation", "FAIL"),
    ("ssh_fingerprint", "FAIL"), ("duplicate", "FAIL"), ("unreachable", "UNKNOWN"),
    ("retired", "UNKNOWN"), ("stale", "UNKNOWN"), ("dns", "FAIL"),
])
def test_eight_scoped_resolvers_acceptance(change, status, tmp_path):
    targets = [
        dict(scope=scope, node=node, ctid=ctid, service=service, hostname=f"fixture-{ctid}",
             host_id=f"identity-{ctid}", incarnation=1, executable="/opt/DnsServerApp.dll",
             ssh_fingerprint=f"SHA256:fixture-{ctid}", canary="probe.example", answer="192.0.2.1")
        for (scope, node, ctid), service in MODULE["TOPOLOGY"].items()
    ]
    evidence = [
        dict(row, proxmox_authenticated=True, ssh_verified=True, active_inventory=True,
             active_service=True, attempt_id="fixture", observed_at=datetime.now(UTC).isoformat(),
             dns=dict.fromkeys(MODULE["DNS_CHECKS"], "ok"))
        for row in targets
    ]
    observed = next(row for row in evidence if row["ctid"] == 600)
    if change in {"scope", "incarnation", "ssh_fingerprint"}:
        observed[change] = 2 if change == "incarnation" else "other"
    if change == "duplicate":
        evidence.append(dict(observed))
    if change == "unreachable":
        observed["collection_status"] = "unreachable"
    if change == "retired":
        observed["active_inventory"] = False
    if change == "stale":
        observed["observed_at"] = "2020-01-01T00:00:00Z"
    if change == "dns":
        observed["dns"]["remote_tcp"] = "timeout"
    evidence += [dict(row, scope="blackwatch", node="pve04") for row in evidence[:8]]
    manifest_file, evidence_file = tmp_path / "approved.json", tmp_path / "evidence.json"
    manifest_file.write_text(json.dumps({"approved": True, "targets": targets}))
    evidence_file.write_text(json.dumps({
        "attempt_status": "succeeded", "attempt_id": "fixture", "targets": evidence,
    }))
    result = subprocess.run([sys.executable, str(SCRIPT), str(manifest_file), str(evidence_file), "--json"],
                            capture_output=True, text=True, check=False)
    rows = json.loads(result.stdout)
    assert len(rows) == 8
    assert next(row for row in rows if row["ctid"] == 600)["status"] == status
    assert result.returncode == (0 if change is None else 1)
