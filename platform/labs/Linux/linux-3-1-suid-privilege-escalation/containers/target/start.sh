#!/bin/bash
# Meridian Data Corp: Build Server startup

# Start SSH
/usr/sbin/sshd

# Start cron (for realism)
cron

echo "[target] Build server online. SSH running"

# Keep container alive
exec sleep infinity
