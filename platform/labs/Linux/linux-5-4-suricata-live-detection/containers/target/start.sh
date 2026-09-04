#!/bin/bash
# Sentinel Defense Corp: Web Portal startup

# Start SSH
/usr/sbin/sshd

# Start nginx
nginx

echo "[target] Web portal online. SSH and nginx running"

# Keep container alive
tail -f /var/log/nginx/access.log
