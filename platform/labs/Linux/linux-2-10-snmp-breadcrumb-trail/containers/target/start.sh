#!/bin/bash
# Generate SSH host keys if missing
ssh-keygen -A 2>/dev/null

# Start SNMP daemon in background
snmpd -C -c /etc/snmp/snmpd.conf -Lo &

# Start SSH daemon in foreground
exec /usr/sbin/sshd -D -e
