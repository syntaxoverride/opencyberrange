#!/bin/bash
# Start SNMP daemon in foreground mode
exec snmpd -f -C -c /etc/snmp/snmpd.conf -Lo
