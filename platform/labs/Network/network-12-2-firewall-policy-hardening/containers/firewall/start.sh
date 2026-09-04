#!/bin/bash

# Enable IP forwarding so this box acts as a router/firewall
echo 1 > /proc/sys/net/ipv4/ip_forward

# Start SSH in foreground
exec /usr/sbin/sshd -D
