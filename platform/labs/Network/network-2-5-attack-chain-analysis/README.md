# Network Lab 2-5: Multi-Stage Attack Chain Analysis

## Lab Overview

This capstone network analysis lab challenges you to analyze a complete multi-stage cyber attack targeting MediCare Health Systems. You'll reconstruct the entire attack timeline from initial compromise through data exfiltration, extracting indicators of compromise and mapping the attack to industry frameworks.

**Difficulty**: Intermediate
**Estimated Time**: 90 minutes
**Category**: Network Security, Incident Response, Threat Hunting

## Learning Objectives

- Understand the cyber attack kill chain and how sophisticated attacks progress
- Identify initial access vectors in network traffic
- Detect command and control (C2) communication patterns
- Track lateral movement using SMB and administrative protocols
- Recognize data exfiltration indicators
- Extract and document indicators of compromise (IOCs)
- Map attacks to the MITRE ATT&CK framework
- Create comprehensive incident timelines for response teams

## Scenario

Marcus Thompson, MediCare Health Systems' Security Analyst, has been called in to investigate a major security incident. The SOC detected suspicious outbound traffic from the patient records department late Friday evening.

Initial triage revealed that multiple systems in the patient records network were compromised, and there are strong indicators that sensitive patient data may have been exfiltrated. The CISO has activated the incident response team and needs a complete analysis.

Marcus has captured 5 hours of network traffic from the affected subnet. Your task is to analyze this traffic and reconstruct the complete attack chain.

## Setup

```bash
# SSH into the analysis workstation
ssh analyst@<target_ip>
# Password: MediCare2024#

# The PCAP file is located at:
# /home/analyst/captures/full-attack.pcap
```

> **Note:** If a GUI is available, Wireshark can also open this PCAP for visual analysis. This walkthrough uses `tshark` (the command-line counterpart) so the lab can be completed entirely from a terminal.

## Attack Chain Background

Modern cyber attacks follow a predictable pattern called the "Cyber Kill Chain":

1. **Reconnaissance**: Gathering information about the target
2. **Weaponization**: Creating or acquiring malicious tools
3. **Delivery**: Sending payload to victim (email, drive-by download, etc.)
4. **Exploitation**: Payload executes and compromises system
5. **Installation**: Malware establishes persistence
6. **Command & Control**: Malware connects to attacker infrastructure
7. **Actions on Objectives**: Data theft, lateral movement, or destruction

In this PCAP, you'll observe stages 3-7 (Delivery through Actions on Objectives).

## Analysis Walkthrough

### Stage 1: Initial Assessment

Start by getting a high-level view of the traffic from the command line.

**Protocol Hierarchy:**

View the distribution of protocols present in the capture:

```bash
tshark -r captures/full-attack.pcap -q -z io,phs
```

- Shows distribution of protocols
- Look for unusual protocols or ratios
- Note: HTTP, DNS, SMB, FTP, TLS/HTTPS

**IP Conversations:**

Identify the top talkers and internal-to-external connections:

```bash
tshark -r captures/full-attack.pcap -q -z conv,ip
```

- Sort by packets and bytes
- Identify top talkers
- Look for internal-to-external connections

**Endpoints:**

List all hosts that appear in the capture:

```bash
tshark -r captures/full-attack.pcap -q -z endpoints,ip
```

- Identify all hosts in the capture
- Note internal network: 10.0.10.0/24
- Note external IPs (non-RFC1918 addresses)

**Key Questions:**
- What internal hosts are present?
- What external IPs appear in the traffic?
- What protocols are most common?
- Are there any unusual protocol ratios?

### Stage 2: Identifying Initial Access

Look for the initial compromise; typically a malicious download.

**tshark Commands:**

```bash
# Show all HTTP GET requests with key fields
tshark -r captures/full-attack.pcap -Y 'http.request.method == "GET"' \
  -T fields -e frame.time -e ip.src -e ip.dst -e http.host -e http.request.uri

# Look for executable downloads
tshark -r captures/full-attack.pcap -Y 'http.request.uri contains ".exe"' \
  -T fields -e frame.time -e ip.src -e http.host -e http.request.uri
```

**What to Look For:**

- Downloads from suspicious domains (not google.com, microsoft.com, etc.)
- Executable files (.exe, .dll, .bat, .ps1, .zip)
- Unusual URLs or paths
- Downloads from uncommon CDNs or infrastructure

**Expected Findings:**

- **Time**: Approximately 30 minutes into the capture (T+30)
- **Source IP**: 10.0.10.25 (victim workstation)
- **Destination**: External IP (malicious infrastructure)
- **Domain**: `malicious-cdn.tk`
- **File**: `system-update.exe`
- **Method**: HTTP GET request

**IOC Documentation:**

```
IOC Type: Domain
Value: malicious-cdn.tk
Context: Initial malware download
Timestamp: [capture time + ~30 min]

IOC Type: IP Address
Value: [external IP]
Context: Malware hosting server
Timestamp: [capture time + ~30 min]

IOC Type: Filename
Value: system-update.exe
Context: Malicious payload
Timestamp: [capture time + ~30 min]
```

### Stage 3: Command & Control (C2) Detection

After infection, malware typically establishes C2 communication with the attacker's server.

**tshark Commands:**

```bash
# Show all TLS Client Hello packets with SNI (Server Name Indication)
tshark -r captures/full-attack.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e frame.time -e ip.src -e ip.dst -e tls.handshake.extensions_server_name

# Count connections per destination from the compromised host
tshark -r captures/full-attack.pcap -Y "ip.src == 10.0.10.25" -T fields \
  -e ip.dst | sort | uniq -c | sort -rn

# Time analysis for beaconing: look for regular intervals
tshark -r captures/full-attack.pcap -Y "ip.src == 10.0.10.25 and ip.dst == [C2_IP]" \
  -T fields -e frame.time_relative
```

**What to Look For:**

- **Beaconing**: Regular, periodic connections at consistent intervals
- **HTTPS to suspicious domains**: Unknown TLDs or random-looking domains
- **Repeated connections**: Same destination contacted many times
- **Small data transfers**: C2 typically sends small commands

**C2 Patterns:**

- Interval: Every 5, 10, or 15 minutes (common beacon intervals)
- Protocol: Usually HTTPS (port 443) to avoid detection
- Domain: Often uses DGA (Domain Generation Algorithm) or suspicious TLD
- Data size: Small encrypted packets (commands are typically small)

**Expected Findings:**

- **Time**: Starts around T+45 minutes, continues throughout capture
- **Source**: 10.0.10.25 (compromised workstation)
- **Destination**: External C2 server
- **Domain**: `c2-server.tk`
- **Interval**: Every 5 minutes (300 seconds)
- **Count**: 12+ beacon connections

**IOC Documentation:**

```
IOC Type: Domain
Value: c2-server.tk
Context: Command and control server
Timestamp: [T+45 onwards]

IOC Type: IP Address
Value: [C2 IP]
Context: C2 server infrastructure
Timestamp: [T+45 onwards]

IOC Type: Network Indicator
Value: HTTPS beaconing every 300 seconds
Context: Malware check-in pattern
```

### Stage 4: Credential Harvesting

Attackers often attempt to harvest credentials to expand their access.

**tshark Commands:**

```bash
# Show all SMB traffic to the domain controller
tshark -r captures/full-attack.pcap -Y "tcp.dport == 445" \
  -T fields -e frame.time -e ip.src -e ip.dst

# Show all SMB Session Setup attempts with status codes
tshark -r captures/full-attack.pcap -Y "smb2.cmd == 1" -T fields \
  -e frame.time -e ip.src -e ip.dst -e smb2.nt_status

# Count failed vs successful authentications
tshark -r captures/full-attack.pcap -Y "smb2.cmd == 1 and smb2.nt_status != 0" \
  | wc -l  # Failed attempts

tshark -r captures/full-attack.pcap -Y "smb2.cmd == 1 and smb2.nt_status == 0" \
  | wc -l  # Successful attempts
```

**What to Look For:**

- Multiple SMB authentication attempts
- Failed logins (NTSTATUS: 0xC000006D - bad username/password)
- Successful authentication after multiple failures
- Connections to Domain Controller (10.0.10.5)

**Expected Findings:**

- **Time**: Around T+90 minutes
- **Source**: 10.0.10.25 (compromised workstation)
- **Destination**: 10.0.10.5 (domain controller)
- **Pattern**: 8+ failed attempts, then 1 successful
- **Technique**: MITRE ATT&CK T1110 - Brute Force

**IOC Documentation:**

```
IOC Type: Behavior
Value: SMB brute force attack
Context: Credential harvesting from domain controller
Timestamp: [T+90 min]
MITRE ATT&CK: T1110.001 - Password Guessing
```

### Stage 5: Lateral Movement

With valid credentials, attackers move to other systems to find valuable data.

**tshark Commands:**

```bash
# Show all SMB connections from compromised host
tshark -r captures/full-attack.pcap -Y "ip.src == 10.0.10.25 and smb2" -T fields \
  -e frame.time -e ip.dst -e smb2.cmd

# Look for tree connect commands (share access)
tshark -r captures/full-attack.pcap -Y "smb2.cmd == 3" -T fields \
  -e frame.time -e ip.src -e ip.dst

# Count file operations (Create and Read)
tshark -r captures/full-attack.pcap -Y "ip.src == 10.0.10.25 and smb2.cmd == 5" \
  | wc -l

# Follow a specific SMB TCP stream for details (replace <stream> with the stream number)
# First, find the stream number from a packet of interest:
tshark -r captures/full-attack.pcap -Y "ip.src == 10.0.10.25 and ip.dst == 10.0.10.50 and smb2" \
  -T fields -e tcp.stream | head -1

# Then follow that stream:
tshark -r captures/full-attack.pcap -q -z follow,tcp,ascii,<stream>
```

**What to Look For:**

- SMB connections from workstation to file servers
- Access to administrative shares (C$, ADMIN$, or custom shares)
- File browsing and reading operations
- Connections to systems that don't normally communicate

**Expected Findings:**

- **Time**: Around T+120 minutes (2 hours)
- **Source**: 10.0.10.25 (compromised workstation)
- **Destination**: 10.0.10.50 (file server)
- **Share**: PatientRecords$ share
- **Operations**: Multiple file read/enumerate operations
- **Technique**: MITRE ATT&CK T1021.002 - SMB/Windows Admin Shares

**IOC Documentation:**

```
IOC Type: Behavior
Value: Lateral movement via SMB
Context: Access to patient records file server
Timestamp: [T+120 min]
MITRE ATT&CK: T1021.002 - Remote Services: SMB/Windows Admin Shares

IOC Type: Target System
Value: 10.0.10.50 (file server)
Context: Patient records repository
```

### Stage 6: Data Exfiltration

The final objective; stealing the data.

**tshark Commands:**

```bash
# Show all FTP commands with arguments
tshark -r captures/full-attack.pcap -Y "ftp" -T fields \
  -e frame.time -e ip.src -e ip.dst -e ftp.request.command -e ftp.request.arg

# Look for STOR command (file upload): this reveals the flag
tshark -r captures/full-attack.pcap -Y 'ftp.request.command == "STOR"' \
  -T fields -e ftp.request.arg

# Calculate total data exfiltrated via FTP-DATA
tshark -r captures/full-attack.pcap -Y "ftp-data" -T fields -e frame.len \
  | awk '{sum+=$1} END {print "Total bytes:", sum}'

# Follow the FTP control stream for full session details
# First find the stream number:
tshark -r captures/full-attack.pcap -Y "ftp" -T fields -e tcp.stream | head -1
# Then follow it:
tshark -r captures/full-attack.pcap -q -z follow,tcp,ascii,<stream>
```

**What to Look For:**

- Large uploads to external servers
- FTP uploads (port 21, FTP-DATA)
- Traffic to unknown external IPs
- Late-night or off-hours activity

**Expected Findings:**

- **Time**: Around T+180 minutes (3 hours)
- **Source**: 10.0.10.25 (compromised workstation)
- **Destination**: 198.51.100.42 (external FTP server)
- **Protocol**: FTP (port 21)
- **File**: `patient-records-OCR{full_4tt4ck_ch41n_m4pp3d}.zip`
- **Size**: ~15 MB
- **FLAG LOCATION**: Embedded in the FTP STOR command filename!
- **Technique**: MITRE ATT&CK T1048.002 - Exfiltration Over Alternative Protocol

**Finding the Flag:**

```bash
# Extract FTP STOR commands: the filename contains the flag
tshark -r captures/full-attack.pcap -Y 'ftp.request.command == "STOR"' \
  -T fields -e ftp.request.arg

# The output will show: patient-records-OCR{full_4tt4ck_ch41n_m4pp3d}.zip
```

**IOC Documentation:**

```
IOC Type: IP Address
Value: 198.51.100.42
Context: Data exfiltration destination
Timestamp: [T+180 min]

IOC Type: Filename
Value: patient-records-OCR{full_4tt4ck_ch41n_m4pp3d}.zip
Context: Exfiltrated patient database
Timestamp: [T+180 min]
MITRE ATT&CK: T1048 - Exfiltration Over Alternative Protocol
```

## Complete Attack Timeline

| Time | Stage | Activity | Source | Destination | IOC |
|------|-------|----------|--------|-------------|-----|
| T+30min | Initial Access | Malicious executable download | 10.0.10.25 | malicious-cdn.tk | system-update.exe |
| T+45min | C2 Setup | First C2 beacon | 10.0.10.25 | c2-server.tk | HTTPS beaconing |
| T+45min - T+105min | C2 Communication | Regular beacons every 5 min | 10.0.10.25 | c2-server.tk | 12+ connections |
| T+90min | Credential Harvesting | SMB brute force | 10.0.10.25 | 10.0.10.5 (DC) | 8 failed + 1 success |
| T+120min | Lateral Movement | SMB to file server | 10.0.10.25 | 10.0.10.50 | PatientRecords$ share |
| T+180min | Data Exfiltration | FTP upload of patient data | 10.0.10.25 | 198.51.100.42 | 15MB patient-records.zip |

## MITRE ATT&CK Mapping

| Tactic | Technique ID | Technique Name | Evidence |
|--------|--------------|----------------|----------|
| Initial Access | T1566.002 | Phishing: Spearphishing Link | HTTP download of malicious executable |
| Execution | T1204.002 | User Execution: Malicious File | system-update.exe executed |
| Command and Control | T1071.001 | Application Layer Protocol: Web Protocols | HTTPS C2 beaconing |
| Command and Control | T1573.002 | Encrypted Channel: Asymmetric Cryptography | TLS-encrypted C2 traffic |
| Credential Access | T1110.001 | Brute Force: Password Guessing | SMB authentication attempts |
| Lateral Movement | T1021.002 | Remote Services: SMB/Windows Admin Shares | SMB to file server |
| Collection | T1039 | Data from Network Shared Drive | Access to PatientRecords$ share |
| Exfiltration | T1048.002 | Exfiltration Over Alternative Protocol | FTP upload to external server |

## Indicators of Compromise (IOCs)

### Network Indicators

```
# Malicious Domains
malicious-cdn.tk
c2-server.tk

# Malicious IP Addresses
185.220.101.73  # Malware hosting
185.220.101.88  # C2 server
198.51.100.42   # Exfiltration server

# Network Patterns
- HTTPS beaconing every 300 seconds
- SMB brute force: 8+ failed authentications
- FTP upload ~15MB to external IP
```

### File Indicators

```
# Malicious Files
system-update.exe  # Initial payload
patient-records-OCR{full_4tt4ck_ch41n_m4pp3d}.zip  # Exfiltrated data
```

### Behavioral Indicators

```
# Host Indicators
- Workstation 10.0.10.25 compromised
- Unusual outbound HTTPS to suspicious TLD (.tk)
- Workstation accessing file server via SMB (unusual)
- FTP client activity from workstation (not normal)

# Timeline Indicators
- Friday evening activity (outside business hours)
- Sustained malicious activity over 3+ hours
- Progressive attack stages indicating human operator
```

## Incident Response Recommendations

### Immediate Actions

1. **Isolate Affected Systems**
   - Disconnect 10.0.10.25 from network immediately
   - Review 10.0.10.50 (file server) for unauthorized access
   - Check domain controller (10.0.10.5) for compromised accounts

2. **Block Malicious Infrastructure**
   - Add malicious-cdn.tk, c2-server.tk to DNS blocklist
   - Block IPs: 185.220.101.73, 185.220.101.88, 198.51.100.42
   - Update firewall rules to prevent future connections

3. **Preserve Evidence**
   - Take memory dump of 10.0.10.25
   - Take disk image of 10.0.10.25
   - Preserve all logs (firewall, proxy, endpoint)
   - Document timeline and findings

### Investigation Actions

1. **Scope Assessment**
   - Search for system-update.exe on all systems
   - Check all workstations for C2 communication to c2-server.tk
   - Review file server access logs for unauthorized access
   - Audit Active Directory for compromised accounts

2. **Data Loss Assessment**
   - Determine what patient records were accessed
   - Estimate number of patients affected
   - Prepare for HIPAA breach notification (if >500 patients)

3. **Root Cause Analysis**
   - How did user download system-update.exe?
   - Was it phishing email? Drive-by download? USB?
   - Why didn't antivirus detect it?
   - Why didn't web filter block malicious-cdn.tk?

### Remediation Actions

1. **Eradication**
   - Reimage 10.0.10.25 completely
   - Reset passwords for all accounts accessed from 10.0.10.25
   - Reset domain admin passwords if compromised
   - Remove persistence mechanisms (scheduled tasks, registry, services)

2. **Recovery**
   - Restore 10.0.10.25 from known-good backup (pre-compromise)
   - Verify file server integrity
   - Monitor all systems for signs of persistence

3. **Lessons Learned**
   - Update security awareness training
   - Implement application whitelisting
   - Deploy EDR (Endpoint Detection and Response)
   - Improve network segmentation
   - Enable SMB signing and disable SMBv1
   - Restrict outbound FTP
   - Implement data loss prevention (DLP)

## Key Takeaways

1. **Attack Chains are Progressive**: Attackers follow predictable patterns that can be detected at each stage
2. **Dwell Time Matters**: This attack took 3 hours from initial access to exfiltration; early detection saves data
3. **Network Monitoring is Critical**: All attack stages generated network indicators
4. **Context is Key**: Understanding normal vs. abnormal behavior is essential (workstations don't normally use FTP or access file servers directly)
5. **Defense in Depth**: Multiple failures allowed this attack (web filtering, antivirus, network monitoring, segmentation)

## Additional Analysis Exercises

1. **Calculate Dwell Time**: How long did the attacker have access before exfiltration?
2. **Estimate Data Loss**: Based on the FTP transfer, how much data was stolen?
3. **Identify Detection Opportunities**: At what points could this attack have been stopped?
4. **Create Yara Rules**: Write rules to detect the malware based on network behavior
5. **Develop Hunting Queries**: Create queries to find similar activity in your environment

## Flag Submission

Once you've identified all attack stages and found the flag in the exfiltration traffic, submit it in the format:

```
OCR{full_4tt4ck_ch41n_m4pp3d}
```

## Resources

- [MITRE ATT&CK Framework](https://attack.mitre.org/)
- [Cyber Kill Chain](https://www.lockheedmartin.com/en-us/capabilities/cyber/cyber-kill-chain.html)
- [tshark Man Page](https://www.wireshark.org/docs/man-pages/tshark.html)
- [tshark Display Filter Reference](https://www.wireshark.org/docs/dfref/)
- [NIST Incident Response Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf)
- [SANS Incident Response Process](https://www.sans.org/reading-room/whitepapers/incident/incident-handlers-handbook-33901)

---

**Lab Author**: OpenCyberRange Team
**Last Updated**: January 2026
**Difficulty**: Intermediate
**Prerequisites**: Network fundamentals, tshark/Wireshark basics, understanding of TCP/IP, SMB, HTTP/HTTPS, FTP
