# Horizon Aerospace: Log Correlation Investigation

## Overview

Students correlate evidence across three sources; a PCAP network capture, SSH authentication logs, and Apache access logs; to reconstruct a coordinated intrusion at Horizon Aerospace. The attacker brute-forced SSH, compromised a service account, uploaded and downloaded sensitive files via HTTP, exfiltrated data over FTP, and used DNS tunneling. Three IOC tokens embedded in the PCAP traffic form the composite flag.

## Architecture

```
┌─────────────┐                      ┌──────────────┐
│   Student    │ ──── SSH:22 ──────▶ │   analyst     │
│   (Kali VM)  │                     │ (SOC workst.) │
└─────────────┘                      └──────────────┘
                                      Contains:
                                      - capture.pcap
                                      - auth.log
                                      - access.log
                                      - case_brief.txt

Evidence correlation across three sources:

  auth.log:
    14:18:xx  Failed SSH from 10.30.1.105 (root, admin, deploy, etc.)
    14:21:33  Successful SSH from 10.30.1.105 as "jenkins"

  access.log:
    14:22:15  POST /upload from 10.30.1.105
    14:22:45  GET /downloads/classified_plans.tar.gz from 10.30.1.105

  capture.pcap:
    HTTP POST with token=c0rr3l4t3 ─────────────── IOC 1
    FTP PASS l0g ────────────────────────────────── IOC 2
    DNS query hunt.exfil.evil-dns.net ───────────── IOC 3
```

## Solution Walkthrough

### Step 1: Connect and Read the Brief

```bash
ssh analyst@<analyst_ip>
# Password: H0r1z0n_S0C#

cat ~/evidence/case_brief.txt
```

### Step 2: Examine Server Logs

```bash
# Review auth.log: look for the attacker IP and compromised account
cat ~/evidence/auth.log
# Key findings:
# - 10.30.1.105 brute-forced SSH at 14:18
# - Successful login as "jenkins" at 14:21:33

# Review access.log: look for the attacker's web activity
cat ~/evidence/access.log
# Key findings:
# - POST /upload from 10.30.1.105 at 14:22:15
# - GET /downloads/classified_plans.tar.gz at 14:22:45
```

### Step 3: Extract IOC 1: HTTP POST Token

```bash
# Filter PCAP for HTTP POST traffic
tcpdump -r ~/evidence/capture.pcap -A dst host 10.30.1.50 | grep token=

# Or with tshark
tshark -r ~/evidence/capture.pcap -Y "http.request.method==POST" -T fields -e http.file_data
```

Look for: `token=c0rr3l4t3` in the POST body.

**IOC 1:** `c0rr3l4t3`

### Step 4: Extract IOC 2: FTP Password

```bash
# Filter for FTP traffic
tcpdump -r ~/evidence/capture.pcap -A port 21 | grep PASS

# Or specifically
tshark -r ~/evidence/capture.pcap -Y "ftp.request.command==PASS" -T fields -e ftp.request.arg
```

Look for: `PASS l0g`

**IOC 2:** `l0g`

### Step 5: Extract IOC 3: DNS Exfiltration

```bash
# Filter for DNS TXT queries to suspicious domain
tcpdump -r ~/evidence/capture.pcap -n port 53 | grep evil-dns

# Or with tshark
tshark -r ~/evidence/capture.pcap -Y "dns.qry.name contains evil-dns" -T fields -e dns.qry.name
```

Look for: `hunt.exfil.evil-dns.net`: the first subdomain label is the IOC.

**IOC 3:** `hunt`

### Step 6: Assemble Flag

```
OCR{c0rr3l4t3_l0g_hunt}
```

## Correlation Summary

| Time (UTC) | Source | Event |
|---|---|---|
| 14:18:01-14:18:31 | auth.log | SSH brute-force from 10.30.1.105 (6 failed attempts) |
| 14:21:33 | auth.log | Successful SSH login as "jenkins" from 10.30.1.105 |
| 14:22:15 | access.log + PCAP | HTTP POST /upload from 10.30.1.105 (token=c0rr3l4t3) |
| 14:22:45 | access.log + PCAP | GET classified_plans.tar.gz from 10.30.1.105 |
| ~14:23:xx | PCAP | FTP session to 203.0.113.50 (PASS l0g, STOR classified_plans) |
| ~14:24:xx | PCAP | DNS exfil queries to hunt.exfil.evil-dns.net |
| 14:25:10 | auth.log | SSH session closed for jenkins |

## Common Mistakes

- **Not reading all three evidence sources.** Students who jump straight to the PCAP miss the context from auth.log and access.log that ties the attack together.
- **Ignoring timestamps.** The correlation between the SSH login at 14:21:33 and the HTTP POST at 14:22:15 is the key link.
- **Focusing on the wrong IP.** Internal hosts 10.30.1.10 and 10.30.1.20 are legitimate; 10.30.1.105 is the attacker.
- **Missing the FTP password.** The PASS command is short and easy to overlook. Filter specifically for port 21.
- **Not recognizing DNS exfiltration.** The TXT queries to evil-dns.net are the covert exfil channel.

## Technical Details

- **PCAP generated with:** Python/scapy during container build
- **Packet count:** ~70 packets covering 5 protocols
- **Protocols:** DNS (A + TXT), HTTP, FTP, TCP handshakes
- **Evidence correlation:** 3 sources (PCAP, auth.log, access.log) with matching timestamps and IPs
- **Attack chain:** SSH brute-force -> account compromise -> HTTP upload/download -> FTP exfil -> DNS exfil
- **Tools available:** tcpdump, tshark, python3/scapy, grep, jq

## Defensive Recommendations

- Enforce SSH key-only authentication; disable password login for service accounts like "jenkins"
- Implement account lockout after repeated failed SSH attempts
- Monitor for outbound FTP connections to unknown external IPs
- Alert on DNS TXT queries to unrecognized domains (DNS exfil signature)
- Correlate logs centrally with a SIEM; the attack pattern is obvious when all sources are combined
- Restrict service accounts to specific source IPs using AllowUsers directives
