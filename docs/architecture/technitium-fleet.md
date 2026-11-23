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
