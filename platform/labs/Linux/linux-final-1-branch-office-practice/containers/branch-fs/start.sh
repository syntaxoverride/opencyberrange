#!/bin/bash
# Atlas Distribution - Branch File Server startup
snmpd -C -c /etc/snmp/snmpd.conf -Lo &
smbd --foreground --no-process-group &
nmbd --foreground --no-process-group &
exec sleep infinity
