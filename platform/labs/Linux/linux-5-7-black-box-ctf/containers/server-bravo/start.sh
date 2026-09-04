#!/bin/bash
# Start SSH and nginx for server-bravo

# Generate SSH host keys if missing
ssh-keygen -A

# Start SSH daemon
/usr/sbin/sshd

# Start nginx in foreground
nginx -g 'daemon off;'
