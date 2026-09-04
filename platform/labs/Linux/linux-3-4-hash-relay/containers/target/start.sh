#!/bin/bash
# Blackrock Dynamics: Server startup

# Start SSH
/usr/sbin/sshd

echo "[target] Blackrock server online. SSH running"

# Keep container alive
exec sleep infinity
