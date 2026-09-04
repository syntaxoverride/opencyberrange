#!/bin/bash
# Cobalt Systems: Monitoring Server startup

# Start SSH
/usr/sbin/sshd

# Start cron (for realism)
cron

echo "[target] Monitoring server online. SSH running"

# Keep container alive
exec sleep infinity
