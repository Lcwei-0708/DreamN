#!/bin/bash
set -e

# Load environment variables
if [ -f /etc/environment ]; then
    export $(cat /etc/environment | xargs)
fi

# Debug: Check if environment variables are loaded
echo "$(date): MYSQL_DATABASE=$MYSQL_DATABASE, MYSQL_USER=$MYSQL_USER" >> /var/log/backup.log

# Variables
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${DATE}.sql"
MAX_BACKUPS=5

mkdir -p "$BACKUP_DIR"

# Check database connection
echo "$(date): Checking database connection..." >> /var/log/backup.log
for i in {1..30}; do
    if mariadb-admin --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" --host=localhost ping >/dev/null 2>&1; then
        echo "$(date): Database connection successful" >> /var/log/backup.log
        break
    fi
    if [ $i -eq 30 ]; then
        echo "$(date): Database connection failed, skipping backup" >> /var/log/backup.log
        exit 0
    fi
    sleep 2
done

# Check if databases exist
echo "$(date): Checking if databases exist..." >> /var/log/backup.log
if ! mariadb --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" --host=localhost -e "USE \`$MYSQL_DATABASE\`;" 2>/dev/null; then
    echo "$(date): Database '$MYSQL_DATABASE' does not exist, skipping backup" >> /var/log/backup.log
    exit 0
fi

if ! mariadb --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" --host=localhost -e "USE \`test_$MYSQL_DATABASE\`;" 2>/dev/null; then
    echo "$(date): Database 'test_$MYSQL_DATABASE' does not exist, skipping backup" >> /var/log/backup.log
    exit 0
fi

echo "$(date): Starting backup..." >> /var/log/backup.log

# Execute backup with error output (using mariadb-dump instead of mysqldump)
mariadb-dump \
    --host=localhost \
    --user="$MYSQL_USER" \
    --password="$MYSQL_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --add-drop-database \
    --databases "$MYSQL_DATABASE" "test_$MYSQL_DATABASE" \
    > "$BACKUP_DIR/$BACKUP_FILE" 2>> /var/log/backup.log

# Check backup success
if [ $? -eq 0 ] && [ -s "$BACKUP_DIR/$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    echo "$(date): Backup successful: $BACKUP_FILE ($BACKUP_SIZE)" >> /var/log/backup.log
else
    echo "$(date): Backup failed! Exit code: $?" >> /var/log/backup.log
    echo "$(date): Backup file size: $(wc -c < "$BACKUP_DIR/$BACKUP_FILE")" >> /var/log/backup.log
    rm -f "$BACKUP_DIR/$BACKUP_FILE"
    exit 1
fi

# Clean old backups
cd "$BACKUP_DIR"
ls -t backup_*.sql 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -f

# Log current status
CURRENT_BACKUPS=$(ls -1 backup_*.sql 2>/dev/null | wc -l)
echo "$(date): Current backups: $CURRENT_BACKUPS (max: $MAX_BACKUPS)" >> /var/log/backup.log 