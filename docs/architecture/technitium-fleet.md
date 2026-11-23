# Technitium fleet monitoring design

Issue #10 extends the existing Technitium health plugin on the current HIMP integration branch. Scheduled and on-demand health runs use the existing inventory selection, host binding, report ingestion and history. The probe uses the inventory SSH transport and records fixed diagnostic fields only. It does not require a Technitium API token.

| Proxmox scope | Node | CTIDs | Incident unit |
| --- | --- | --- | --- |
| BlackWatch cluster | pve01 | 310, 311 | dns.service |
| BlackWatch cluster | pve02 | 312, 313 | dns.service |
| Standalone | pve | 800, 801 | technitium.service |
| Standalone | prox | 600, 601 | technitium.service |

Inventory contains eight Technitium targets. The incident provides hypervisor and CT pairs but does not prove the mapping of each pair to an inventory hostname or establish current reachability. Confirm those mappings with authoritative Proxmox evidence before correlating backups. Use the HIMP host ID and incarnation for monitoring history and a verified Proxmox scope ID, node and CTID for backup joins.

## Phase contracts

- Health collection reads fixed systemd properties and uses bounded targeted DNS queries. A controlled record and expected address configure answer verification. Missing configuration or tools produce explicit unknown results. Collect effective UID, process ID, restart counter and boot ID. Compare counters only on the same host incarnation and boot, and record resets and stale samples distinctly.
- Evaluate equivalent enabled units using their full executable arguments and deduplicate systemd aliases by canonical ID. Collect only the resulting comparison and allowlisted service metadata. Do not persist command lines, environment variables or resolver answer text.
- Capacity samples use filesystem blocks and inodes, directory sizes, and strict dated log-file metadata. Use 80% warning and 90% critical with hysteresis, plus free-space and growth rules. Report successful retention execution only from positive evidence. PBS freshness and restore verification require independent authoritative evidence.
- Read views inherit HIMP authentication and show observation age, failure reason and recommended diagnostic. Alert events must deduplicate by host incarnation and condition, respect maintenance suppression and preserve operator acknowledgment.
- Guided maintenance is read-only. Before any future authorized mutation, require exact identity, healthy alternate resolver, validated preconditions, backup evidence where applicable, rollback and individual admin approval.
- Validate locally with fixtures and simulated command failures. Release acceptance additionally requires all eight authoritative bindings, isolated restore and non-root migration testing, and a monitored soak. Use unreachable for transport failure, no_permission for explicit denial, not_installed for confirmed absence, and unknown for insufficient evidence.

## Attempt status and SSH trust

The health API and dashboard distinguish the newest collection attempt from the last admitted report. A failed or running attempt makes earlier evidence stale. The last report stays available for historical analysis. Direct API execution requires an administrator session, consistent with the existing automation and workflow execution routes. The server chooses the configured plugin inventory group. API query parameters cannot expand it.

The repository currently sets `host_key_checking = False`. Production deployment requires verified host keys in the controller service account's known-hosts file and strict checking enabled in the effective SSH configuration. Obtain fingerprints through an authenticated management channel and verify the effective settings for both deployment types in staging. Treat unknown or changed keys as a collection failure pending operator review. Verify Proxmox scope, node and CTID before associating backup evidence. A CTID or inventory hostname alone does not authenticate a host.

The HIMP Technitium runner applies strict OpenSSH verification even when the shared Ansible default is permissive. It disables multiplexing and automatic host-key updates for health collection. Enroll the verified endpoint key in the controller account's operator-managed known-hosts file before enabling the schedule. A replacement or reassigned IP requires an independently verified replacement fingerprint and inventory incarnation review before updating the trust entry. Never use automatic acceptance for enrollment. The runner reports initial host-key verification failures as `ssh_identity_failed` with UNKNOWN health. Direct standalone playbook invocation is a development interface and must use independently configured SSH trust.

## Read-only acceptance checklist

Use approved exports from Proxmox and HIMP and a controlled DNS record. The expected maintenance mappings are BlackWatch pve01 CT 310/311 and pve02 CT 312/313 with dns.service, standalone pve CT 800/801 and standalone prox CT 600/601 with technitium.service. Treat these as expected values until verified.

1. Record each management endpoint's independently authenticated environment identity. Join node and CTID inside that scope, then verify the container hostname and management IP against the current HIMP host ID and incarnation. Reject missing or ambiguous joins.
2. Verify controller SSH trust against the authenticated endpoint fingerprint. Validate the intended primary unit and document any inactive alternate. Confirm the canary's owner and expected A record are authorized for the test.
3. Run the read-only health check in the approved environment. Record the current attempt ID and status, each host identity, active unit, DNS UDP/TCP outcomes, and observation time. Require all expected rows and current evidence before sign-off.

The restart warning currently uses a proposed default of three or more additional restarts within 900 seconds between comparable observations. Treat counter decreases and changes to boot identity or host incarnation as a new baseline.
