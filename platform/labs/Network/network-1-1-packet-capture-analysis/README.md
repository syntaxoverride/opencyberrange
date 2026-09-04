# Avalon Biotech: Suspicious Traffic Analysis

## Overview

Students analyze a pre-generated packet capture containing evidence of insider data exfiltration. The PCAP includes normal background traffic mixed with three suspicious channels: an HTTP POST leaking credentials to an external C2 server, an FTP session transferring files to an external host, and DNS TXT queries used for data exfiltration. Each channel contains one IOC marker.

## Architecture

```
┌─────────────┐                      ┌──────────────┐
│   Student    │ ──── SSH:22 ──────▶ │   analyst     │
│   (Kali VM)  │                     │ (SOC workst.) │
└─────────────┘                      └──────────────┘
                                      Contains:
                                      - capture.pcap
                                      - case_brief.txt
                                      - tcpdump, tshark, scapy

PCAP contains traffic from 10.20.1.105 → multiple destinations:
  ┌───────────────────┐
  │ Suspect WS        │──HTTP POST──▶ 198.51.100.47  (C2: IOC 1)
  │ 10.20.1.105       │──FTP────────▶ 203.0.113.22   (Exfil: IOC 2)
  │                   │──DNS TXT────▶ 185.199.108.99 (DNS exfil: IOC 3)
  └───────────────────┘
```

## Solution Walkthrough

### Step 1: Connect and Read the Brief

```bash
ssh analyst@<analyst_ip>
# Password: Av4l0n_S0C#

cat ~/evidence/case_brief.txt
```

### Step 2: Initial PCAP Overview

```bash
# Packet count and protocols
tcpdump -r ~/evidence/capture.pcap -n | wc -l
tcpdump -r ~/evidence/capture.pcap -n | head -20

# Or with tshark
tshark -r ~/evidence/capture.pcap -q -z conv,ip
```

### Step 3: Extract IOC 1: HTTP POST to External C2

```bash
# Filter for HTTP traffic to external IPs
tcpdump -r ~/evidence/capture.pcap -A dst host 198.51.100.47

# Or with tshark
tshark -r ~/evidence/capture.pcap -Y "ip.dst==198.51.100.47 and http" -V
```

Look for: `token=p4ck3t` in the POST body.

**IOC 1:** `p4ck3t`

### Step 4: Extract IOC 2: FTP Password

```bash
# Filter for FTP traffic
tcpdump -r ~/evidence/capture.pcap -A port 21

# Or specifically PASS command
tshark -r ~/evidence/capture.pcap -Y "ftp.request.command==PASS" -T fields -e ftp.request.arg
```

Look for: `PASS 4n4lyz3`

**IOC 2:** `4n4lyz3`

### Step 5: Extract IOC 3: DNS Exfiltration

```bash
# Filter for DNS TXT queries
tcpdump -r ~/evidence/capture.pcap -n port 53 | grep evil-c2

# Or with tshark
tshark -r ~/evidence/capture.pcap -Y "dns.qry.name contains evil-c2" -T fields -e dns.qry.name
```

Look for: `3xf1l.data.evil-c2.net`: the first subdomain label is the IOC.

**IOC 3:** `3xf1l`

### Step 6: Assemble Flag

```
OCR{p4ck3t_4n4lyz3_3xf1l}
```

## Common Mistakes

- **Drowning in noise.** The capture has normal internal traffic. Filter early: `ip.dst != 10.20.1.0/24` or target specific external IPs.
- **Not using `-A` with tcpdump.** Without `-A`, payload data isn't shown. Use `-A` for ASCII output or `-X` for hex+ASCII.
- **Missing the FTP password.** The PASS command is easy to miss among other FTP commands. Filter specifically for `port 21`.
- **Not recognizing DNS exfiltration.** Students may skip DNS traffic entirely. The TXT query type and external DNS server (not the internal 10.20.1.2) are the red flags.
- **Confusing internal vs external traffic.** The 10.20.1.x addresses are internal (normal). The 198.51.x, 203.0.x, and 185.199.x addresses are external (suspicious).

## Technical Details

- **PCAP generated with:** Python/scapy during container build
- **Packet count:** ~60 packets covering 5 protocols
- **Protocols:** DNS (A + TXT), HTTP, FTP, TCP handshakes
- **Exfil methods demonstrated:** HTTP POST (credential leak), FTP (file transfer), DNS TXT (covert channel)
- **Tools available:** tcpdump, tshark, python3/scapy, strings, grep

## Defensive Recommendations

- Monitor for outbound FTP connections; FTP is rarely legitimate in modern environments
- Alert on DNS TXT queries to unrecognized external domains (DNS exfil signature)
- Inspect outbound HTTP POST bodies for sensitive data patterns
- Implement DLP (Data Loss Prevention) at network egress points
- Segment R&D networks with strict outbound filtering
- Use DNS sinkholing for known-bad domains
