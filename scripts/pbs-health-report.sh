#!/bin/bash

REPORT_DIR="$HOME/Homelab-Automation/reports/current/pbs"

mkdir -p "$REPORT_DIR"

DATE=$(date)

for HOST in pbs01 pbs02
do

FILE="$REPORT_DIR/$HOST.md"

echo "# $HOST Health Report" > "$FILE"
echo "" >> "$FILE"

echo "Generated: $DATE" >> "$FILE"
echo "" >> "$FILE"


echo "## Health Summary" >> "$FILE"
echo "" >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "echo 'PBS Services:'; systemctl is-active proxmox-backup proxmox-backup-proxy; echo; echo 'Datastore:'; df -h /backup | tail -1" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"


echo "" >> "$FILE"

echo "## System" >> "$FILE"
echo "" >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "hostname; uptime; uname -r" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"


echo "" >> "$FILE"

echo "## CPU / Memory" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "free -h; echo; top -bn1 | head -5" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


echo "" >> "$FILE"

echo "## Storage" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "df -h" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


echo "" >> "$FILE"

echo "## PBS Services" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "systemctl is-active proxmox-backup proxmox-backup-proxy; systemctl is-enabled proxmox-backup proxmox-backup-proxy" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


echo "" >> "$FILE"

echo "## Datastores" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "proxmox-backup-manager datastore list" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


echo "" >> "$FILE"

echo "## Backup Storage Usage" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "du -sh /backup; df -h /backup" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


echo "" >> "$FILE"

echo "## Verification Jobs" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "proxmox-backup-manager verify-job list" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


echo "" >> "$FILE"

echo "## Recent Errors" >> "$FILE"
echo "" >> "$FILE"

echo '```' >> "$FILE"

ansible "$HOST" \
-i inventory/hosts.yml \
-m shell \
-a "journalctl -u proxmox-backup-proxy -p warning..alert -n 20 --no-pager" \
| sed '/SUCCESS/d;/CHANGED/d' >> "$FILE"

echo '```' >> "$FILE"


done
