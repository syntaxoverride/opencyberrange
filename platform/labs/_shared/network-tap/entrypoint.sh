#!/bin/bash
# Network Tap: streams live PCAP data over TCP port 9999.
# Students connect from their own machine:
#   nc <tap-ip> 9999 | tcpdump -r - -A 'port 80'
#   nc <tap-ip> 9999 | wireshark -k -i -
#   nc <tap-ip> 9999 > capture.pcap

# Enable promiscuous mode so we see ALL bridge traffic, not just ours
ip link set eth0 promisc on 2>/dev/null

# BPF filter: exclude our own management traffic (port 9999)
FILTER="not port 9999"

# socat listens on TCP 9999 and forks a tcpdump for each connection.
# -U = packet-buffered output (flush after each packet for real-time streaming)
# -w - = write pcap to stdout (binary pcap format)
exec socat TCP-LISTEN:9999,reuseaddr,fork \
    EXEC:"tcpdump -i eth0 -U -w - ${FILTER}",nofork
