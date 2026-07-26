#!/bin/bash

REPORT_DIR="$HOME/Homelab-Automation/reports/current/proxmox"

mkdir -p "$REPORT_DIR"

DATE=$(date)

for HOST in $(ansible-inventory -i inventory/hosts.yml --list | jq -r '.proxmox.hosts[]')
do

FILE="$REPORT_DIR/$HOST.md"

echo "# $HOST Health Report" > "$FILE"
echo "" >> "$FILE"

echo "Generated: $DATE" >> "$FILE"
echo "" >> "$FILE"


########################################
# Health Summary
########################################

echo "## Health Summary" >> "$FILE"
echo "" >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "hostname; uptime; uname -r; systemctl is-active pve-cluster pvedaemon pveproxy" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"


########################################
# Software Version
########################################

echo "" >> "$FILE"
echo "## Software Version" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "pveversion -v | egrep 'proxmox-ve|pve-manager|corosync|pve-cluster|qemu-server|lxc-pve|proxmox-backup-client'" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# Hardware Inventory
########################################

echo "" >> "$FILE"
echo "## Hardware Inventory" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "echo CPU; lscpu | grep 'Model name'; echo; echo MEMORY; free -h | head -2; echo; echo BIOS; dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release'; echo; echo NETWORK; ip -br addr | grep -E 'vmbr|nic|eno|enp|eth|bond'; echo; echo DISKS; lsblk; echo; echo SMART HEALTH; smartctl -H /dev/nvme0n1 2>/dev/null" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# Cluster Status
########################################

echo "" >> "$FILE"
echo "## Cluster Status" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "pvecm status" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# CPU Memory
########################################

echo "" >> "$FILE"
echo "## CPU / Memory" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "free -h; echo; uptime" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# Storage
########################################

echo "" >> "$FILE"
echo "## Storage" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "pvesm status" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# PBS Connections
########################################

echo "" >> "$FILE"
echo "## PBS Connections" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "pvesm status | grep pbs" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# Virtual Machines
########################################

echo "" >> "$FILE"
echo "## Virtual Machines" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "qm list" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# Containers
########################################

echo "" >> "$FILE"
echo "## Containers" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "pct list" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# Replication
########################################

echo "" >> "$FILE"
echo "## Replication" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "pvesr status" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


########################################
# Recent Errors
########################################

echo "" >> "$FILE"
echo "## Recent Errors" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "journalctl -p warning..alert -n 20 --no-pager" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


done

