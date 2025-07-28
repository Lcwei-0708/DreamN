#!/bin/bash
set -e

# Set timezone
if [ -n "$TZ" ]; then
  ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
  echo "$TZ" > /etc/timezone
else
  ln -sf "/usr/share/zoneinfo/UTC" /etc/localtime
  echo "UTC" > /etc/timezone
fi

# Save environment variables for cron
env | grep -E '^(MYSQL_|TZ=)' > /etc/environment

# Setup backup service
chmod +x /backup.sh
mkdir -p /backups
chown -R root:root /backups

# Create log files
mkdir -p /var/log
touch /var/log/backup.log
touch /var/log/cron
chown root:root /var/log/backup.log
chown root:root /var/log/cron
chmod 644 /var/log/backup.log
chmod 644 /var/log/cron

# Setup crontab
echo "0 0 1 * * /backup.sh >> /var/log/backup.log 2>&1" | crontab -

# Start cron service
service cron start

# Execute original MariaDB entrypoint
exec /usr/local/bin/docker-entrypoint.sh "$@"