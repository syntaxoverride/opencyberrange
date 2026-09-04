#!/bin/bash
# Start SSH for server-delta

# Generate SSH host keys if missing
ssh-keygen -A

# Start SSH daemon in foreground
/usr/sbin/sshd -D
