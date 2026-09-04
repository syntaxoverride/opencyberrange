#!/usr/bin/env python3
"""Generate evidence PCAP for server-delta with HTTP POST containing token."""

from scapy.all import IP, TCP, Raw, wrpcap

# Create raw TCP packets with HTTP payload
pkt = (
    IP(src="10.30.1.105", dst="10.30.1.50")
    / TCP(sport=54321, dport=80, flags="PA")
    / Raw(
        load=(
            "POST /upload HTTP/1.1\r\n"
            "Host: 10.30.1.50\r\n"
            "Content-Type: application/x-www-form-urlencoded\r\n"
            "\r\n"
            "token=pwn&data=classified"
        )
    )
)

wrpcap("/home/analyst/evidence/traffic.pcap", [pkt])
print("PCAP generated successfully.")
