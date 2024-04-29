# Check if a new snapshot has been taken.
# Otherwise, send an email through exim4
#
# This script must run every 24 hours as a cronjob:
# 0 0 * * * /bin/bash /mnt/ai4-logs/ai4-accounting/check_snapshot.sh

# Backups directory
backup_dir="/mnt/ai4os-logs/ai4-accounting/snapshots"

# File with last backup name
last_backup_file="/etc/.last_backup.txt"

if [[ ! -f "$last_backup_file" ]]; then
    touch "$last_backup_file"
fi

read -r last_backup sent < $last_backup_file

new_backup=$(ls -t "$backup_dir" | head -n1)

if [[ "$new_backup" != "$last_backup" ]]; then
    echo "$new_backup" 'false' > "$last_backup_file"
elif [[ "$sent" = 'false' ]]; then
    echo "$new_backup" 'true' > "$last_backup_file"
    echo 'No new ai4-accounting snapshots have been detected in the last 12 hours' | mail -s "⚠️  SNAPSHOT ERROR ⚠️" iheredia@ifca.unican.es
fi
