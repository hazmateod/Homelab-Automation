#!/bin/bash

REPORT_DIR="$HOME/Homelab-Automation/reports/current"

mkdir -p "$REPORT_DIR"

DATE=$(date)

echo "Generating Homelab Health Report"
echo "$DATE"

###################################
# PBS HEALTH
###################################

for HOST in pbs01 pbs02
do

echo "Checking $HOST"

ansible "$HOST" -i inventory/hosts.yml \
-m shell \
-a "hostname; uptime; df -h /; systemctl is-active proxmox-backup" \
> "$REPORT_DIR/$HOST.md"

done


###################################
# TECHNITIUM HEALTH
###################################

for HOST in $(ansible technitium -i inventory/hosts.yml --list-hosts | tail -n +2)
do

echo "Checking $HOST"

ansible "$HOST" -i inventory/hosts.yml \
-m shell \
-a "hostname; uptime; systemctl is-active technitium.service; ss -tulpn | grep 5380" \
> "$REPORT_DIR/$HOST.md"

done


###################################
# SUMMARY
###################################

echo "# Homelab Health Summary" > "$REPORT_DIR/summary.md"

echo "" >> "$REPORT_DIR/summary.md"

echo "Generated: $DATE" >> "$REPORT_DIR/summary.md"

echo "" >> "$REPORT_DIR/summary.md"

ls -1 "$REPORT_DIR" >> "$REPORT_DIR/summary.md"

echo "Complete"

