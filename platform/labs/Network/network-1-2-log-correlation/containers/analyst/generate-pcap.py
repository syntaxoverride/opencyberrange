#!/usr/bin/env python3
"""
Generate a realistic packet capture for the Horizon Aerospace log correlation lab.

The PCAP contains:
  - Normal HTTP traffic to 10.30.1.50 (internal web server)
  - Suspicious HTTP POST from 10.30.1.105 (attacker) with IOC marker 1 (c0rr3l4t3)
  - FTP session from 10.30.1.105 to 203.0.113.50 with IOC marker 2 in PASS cmd (l0g)
  - DNS TXT exfiltration queries with IOC marker 3 (hunt)

Uses scapy to construct packets with proper protocol dissection support.
"""

from scapy.all import (
    Ether, IP, TCP, UDP, DNS, DNSQR, Raw,
    wrpcap
)

# -- Network topology ---------------------------------------------------------
ATTACKER    = "10.30.1.105"       # Attacker IP
WEB_SERVER  = "10.30.1.50"        # Horizon internal web server
DNS_SERVER  = "10.30.1.2"         # Internal DNS resolver
INTERNAL_1  = "10.30.1.10"        # Normal internal host
INTERNAL_2  = "10.30.1.20"        # Normal internal host
EXTERNAL_FTP = "203.0.113.50"     # External FTP staging server
EVIL_DNS    = "185.199.108.99"    # Malicious DNS server

MAC_ATK = "02:00:0a:1e:01:69"
MAC_GW  = "02:00:0a:1e:01:01"
MAC_SRV = "02:00:0a:1e:01:32"
MAC_DNS = "02:00:0a:1e:01:02"
MAC_IN1 = "02:00:0a:1e:01:0a"
MAC_IN2 = "02:00:0a:1e:01:14"

pkts = []
ts = 1726145700.0  # Base timestamp: 2024-09-12 14:15:00 UTC


def add_pkt(pkt, offset=0.0):
    """Add a packet with a specific timestamp offset."""
    global ts
    ts += offset
    pkt.time = ts
    pkts.append(pkt)


# =============================================================================
# Phase 1: Normal background traffic (14:15:00 - 14:20:00)
# =============================================================================

# DNS lookups from internal hosts
for i, domain in enumerate(["intranet.horizon-aero.local", "mail.horizon-aero.local",
                              "jira.horizon-aero.local", "wiki.horizon-aero.local"]):
    add_pkt(
        Ether(src=MAC_IN1, dst=MAC_DNS) /
        IP(src=INTERNAL_1, dst=DNS_SERVER) /
        UDP(sport=49152+i, dport=53) /
        DNS(rd=1, qd=DNSQR(qname=domain, qtype="A")),
        offset=2.0
    )
    add_pkt(
        Ether(src=MAC_DNS, dst=MAC_IN1) /
        IP(src=DNS_SERVER, dst=INTERNAL_1) /
        UDP(sport=53, dport=49152+i) /
        DNS(qr=1, aa=1, qd=DNSQR(qname=domain, qtype="A")),
        offset=0.05
    )

# Normal HTTP GET from 10.30.1.10 to web server
for i, page in enumerate(["index.html", "projects/avionics.html",
                           "hr/directory.html", "it/status.html"]):
    sport = 50000 + i
    add_pkt(
        Ether(src=MAC_IN1, dst=MAC_SRV) /
        IP(src=INTERNAL_1, dst=WEB_SERVER) /
        TCP(sport=sport, dport=80, flags="S", seq=1000+i*1000),
        offset=3.0
    )
    add_pkt(
        Ether(src=MAC_SRV, dst=MAC_IN1) /
        IP(src=WEB_SERVER, dst=INTERNAL_1) /
        TCP(sport=80, dport=sport, flags="SA", seq=5000+i*1000, ack=1001+i*1000),
        offset=0.02
    )
    add_pkt(
        Ether(src=MAC_IN1, dst=MAC_SRV) /
        IP(src=INTERNAL_1, dst=WEB_SERVER) /
        TCP(sport=sport, dport=80, flags="PA", seq=1001+i*1000, ack=5001+i*1000) /
        Raw(load=f"GET /{page} HTTP/1.1\r\nHost: intranet.horizon-aero.local\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: text/html\r\n\r\n".encode()),
        offset=0.01
    )
    add_pkt(
        Ether(src=MAC_SRV, dst=MAC_IN1) /
        IP(src=WEB_SERVER, dst=INTERNAL_1) /
        TCP(sport=80, dport=sport, flags="PA", seq=5001+i*1000, ack=1200+i*1000) /
        Raw(load=f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nServer: Apache/2.4.57\r\n\r\n<html><body>Horizon Aerospace - {page}</body></html>".encode()),
        offset=0.08
    )

# Normal HTTP GET from 10.30.1.20
for i, page in enumerate(["news.html", "engineering/schedule.html"]):
    sport = 50100 + i
    add_pkt(
        Ether(src=MAC_IN2, dst=MAC_SRV) /
        IP(src=INTERNAL_2, dst=WEB_SERVER) /
        TCP(sport=sport, dport=80, flags="PA", seq=2000+i*1000, ack=6000+i*1000) /
        Raw(load=f"GET /{page} HTTP/1.1\r\nHost: intranet.horizon-aero.local\r\nUser-Agent: Mozilla/5.0 (X11; Linux x86_64)\r\n\r\n".encode()),
        offset=4.0
    )


# =============================================================================
# Phase 2: Suspicious HTTP POST from attacker (IOC 1: c0rr3l4t3)
# Timestamp ~14:22:15 UTC. correlates with access.log
# =============================================================================

c2_sport = 51234

# SYN
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_SRV) /
    IP(src=ATTACKER, dst=WEB_SERVER) /
    TCP(sport=c2_sport, dport=80, flags="S", seq=10000),
    offset=120.0  # jump to ~14:22
)
# SYN-ACK
add_pkt(
    Ether(src=MAC_SRV, dst=MAC_ATK) /
    IP(src=WEB_SERVER, dst=ATTACKER) /
    TCP(sport=80, dport=c2_sport, flags="SA", seq=20000, ack=10001),
    offset=0.02
)
# ACK
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_SRV) /
    IP(src=ATTACKER, dst=WEB_SERVER) /
    TCP(sport=c2_sport, dport=80, flags="A", seq=10001, ack=20001),
    offset=0.01
)

# POST with exfil data and IOC marker 1
post_body = "user=jenkins&token=c0rr3l4t3&cmd=upload&file=classified_plans.tar.gz&size=48372816"
post_request = (
    f"POST /upload HTTP/1.1\r\n"
    f"Host: 10.30.1.50\r\n"
    f"User-Agent: curl/7.88.1\r\n"
    f"Content-Type: application/x-www-form-urlencoded\r\n"
    f"Content-Length: {len(post_body)}\r\n"
    f"X-Forwarded-For: 10.30.1.105\r\n"
    f"\r\n"
    f"{post_body}"
)
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_SRV) /
    IP(src=ATTACKER, dst=WEB_SERVER) /
    TCP(sport=c2_sport, dport=80, flags="PA", seq=10001, ack=20001) /
    Raw(load=post_request.encode()),
    offset=0.02
)

# Server response
srv_response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"uploaded\",\"bytes\":48372816}"
add_pkt(
    Ether(src=MAC_SRV, dst=MAC_ATK) /
    IP(src=WEB_SERVER, dst=ATTACKER) /
    TCP(sport=80, dport=c2_sport, flags="PA", seq=20001, ack=10001+len(post_request)) /
    Raw(load=srv_response.encode()),
    offset=0.18
)

# GET for the classified file. matches access.log at 14:22:45
get_sport = 51240
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_SRV) /
    IP(src=ATTACKER, dst=WEB_SERVER) /
    TCP(sport=get_sport, dport=80, flags="PA", seq=11000, ack=21000) /
    Raw(load=b"GET /downloads/classified_plans.tar.gz HTTP/1.1\r\nHost: 10.30.1.50\r\nUser-Agent: curl/7.88.1\r\n\r\n"),
    offset=30.0
)


# =============================================================================
# Phase 3: FTP session to external staging server (IOC 2: l0g)
# =============================================================================

ftp_sport = 52000

# SYN
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_GW) /
    IP(src=ATTACKER, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="S", seq=30000),
    offset=10.0
)
# SYN-ACK
add_pkt(
    Ether(src=MAC_GW, dst=MAC_ATK) /
    IP(src=EXTERNAL_FTP, dst=ATTACKER) /
    TCP(sport=21, dport=ftp_sport, flags="SA", seq=40000, ack=30001),
    offset=0.12
)
# ACK
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_GW) /
    IP(src=ATTACKER, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="A", seq=30001, ack=40001),
    offset=0.01
)

# FTP banner
add_pkt(
    Ether(src=MAC_GW, dst=MAC_ATK) /
    IP(src=EXTERNAL_FTP, dst=ATTACKER) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40001, ack=30001) /
    Raw(load=b"220 vsftpd 3.0.5 ready.\r\n"),
    offset=0.05
)

# USER command
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_GW) /
    IP(src=ATTACKER, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="PA", seq=30001, ack=40026) /
    Raw(load=b"USER dropbox\r\n"),
    offset=0.3
)

# 331 response
add_pkt(
    Ether(src=MAC_GW, dst=MAC_ATK) /
    IP(src=EXTERNAL_FTP, dst=ATTACKER) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40026, ack=30015) /
    Raw(load=b"331 Password required for dropbox.\r\n"),
    offset=0.1
)

# PASS command. contains IOC marker 2
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_GW) /
    IP(src=ATTACKER, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="PA", seq=30015, ack=40062) /
    Raw(load=b"PASS l0g\r\n"),
    offset=0.5
)

# 230 Login successful
add_pkt(
    Ether(src=MAC_GW, dst=MAC_ATK) /
    IP(src=EXTERNAL_FTP, dst=ATTACKER) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40062, ack=30025) /
    Raw(load=b"230 User dropbox logged in.\r\n"),
    offset=0.08
)

# STOR command
add_pkt(
    Ether(src=MAC_ATK, dst=MAC_GW) /
    IP(src=ATTACKER, dst=EXTERNAL_FTP) /
    TCP(sport=ftp_sport, dport=21, flags="PA", seq=30025, ack=40090) /
    Raw(load=b"STOR classified_plans.tar.gz\r\n"),
    offset=1.2
)

# 150 Opening data connection
add_pkt(
    Ether(src=MAC_GW, dst=MAC_ATK) /
    IP(src=EXTERNAL_FTP, dst=ATTACKER) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40090, ack=30055) /
    Raw(load=b"150 Opening BINARY mode data connection for classified_plans.tar.gz\r\n"),
    offset=0.1
)

# 226 Transfer complete
add_pkt(
    Ether(src=MAC_GW, dst=MAC_ATK) /
    IP(src=EXTERNAL_FTP, dst=ATTACKER) /
    TCP(sport=21, dport=ftp_sport, flags="PA", seq=40160, ack=30055) /
    Raw(load=b"226 Transfer complete. 48372816 bytes sent.\r\n"),
    offset=3.0
)


# =============================================================================
# Phase 4: DNS exfiltration queries (IOC 3: hunt)
# =============================================================================

dns_queries = [
    ("init.exfil.evil-dns.net", "TXT"),
    ("chunk1.exfil.evil-dns.net", "TXT"),
    ("Y2xhc3NpZmllZF9wbGFucw.exfil.evil-dns.net", "TXT"),   # base64 encoded
    ("token_hunt.exfil.evil-dns.net", "TXT"),                 # IOC marker 3
    ("chunk2.exfil.evil-dns.net", "TXT"),
    ("ZXhmaWxfY29tcGxldGU.exfil.evil-dns.net", "TXT"),       # base64 encoded
    ("fin.exfil.evil-dns.net", "TXT"),
]

for i, (qname, qtype) in enumerate(dns_queries):
    add_pkt(
        Ether(src=MAC_ATK, dst=MAC_GW) /
        IP(src=ATTACKER, dst=EVIL_DNS) /
        UDP(sport=12346+i, dport=53) /
        DNS(rd=1, qd=DNSQR(qname=qname, qtype=16)),
        offset=1.5
    )
    add_pkt(
        Ether(src=MAC_GW, dst=MAC_ATK) /
        IP(src=EVIL_DNS, dst=ATTACKER) /
        UDP(sport=53, dport=12346+i) /
        DNS(qr=1, aa=1, qd=DNSQR(qname=qname, qtype=16)),
        offset=0.08
    )


# =============================================================================
# Phase 5: More normal traffic (cover)
# =============================================================================

for i, domain in enumerate(["vpn.horizon-aero.local", "git.horizon-aero.local"]):
    add_pkt(
        Ether(src=MAC_IN2, dst=MAC_DNS) /
        IP(src=INTERNAL_2, dst=DNS_SERVER) /
        UDP(sport=49200+i, dport=53) /
        DNS(rd=1, qd=DNSQR(qname=domain, qtype="A")),
        offset=3.0
    )

# Final normal browsing
add_pkt(
    Ether(src=MAC_IN1, dst=MAC_SRV) /
    IP(src=INTERNAL_1, dst=WEB_SERVER) /
    TCP(sport=50200, dport=80, flags="PA", seq=70000, ack=80000) /
    Raw(load=b"GET /hr/timesheet.html HTTP/1.1\r\nHost: intranet.horizon-aero.local\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n\r\n"),
    offset=2.0
)


# =============================================================================
# Write PCAP
# =============================================================================

wrpcap("/home/analyst/evidence/capture.pcap", pkts)
print(f"[+] Generated capture.pcap with {len(pkts)} packets")
print(f"[+] IOC 1 (HTTP POST token): c0rr3l4t3")
print(f"[+] IOC 2 (FTP password):    l0g")
print(f"[+] IOC 3 (DNS exfil label):  hunt")
