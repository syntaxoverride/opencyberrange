#!/bin/bash
# Aegis Security Corp: IDS Sensor startup

# Start SSH server
/usr/sbin/sshd

# Start honeypot nginx (accepts all HTTP requests for Suricata to observe)
nginx

# Prepare Suricata directories
mkdir -p /var/run/suricata /var/log/suricata

# Start Suricata in IDS mode on eth0
# -D = daemon mode, --init-errors-fatal = exit if config is broken
suricata -c /etc/suricata/suricata.yaml -i eth0 -D \
    --pidfile /var/run/suricata/suricata.pid \
    2>/var/log/suricata/suricata-startup.log

echo "[sensor] IDS sensor online. SSH, nginx (honeypot), Suricata running"

# Keep container alive by tailing the Suricata log
exec tail -f /var/log/suricata/suricata.log 2>/dev/null || exec sleep infinity
