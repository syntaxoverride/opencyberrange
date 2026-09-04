#!/bin/bash
# Generate host keys if missing
ssh-keygen -A 2>/dev/null

# Start SSH daemon in foreground
exec /usr/sbin/sshd -D -e
