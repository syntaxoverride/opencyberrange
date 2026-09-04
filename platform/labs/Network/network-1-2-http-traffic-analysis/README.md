# HTTP Traffic Analysis - Walkthrough

## Lab Overview

This lab teaches network security fundamentals by analyzing a packet capture (PCAP) to identify cleartext credentials transmitted over HTTP. You'll learn why HTTPS encryption is critical for protecting sensitive data and how attackers can intercept unencrypted traffic.

**Difficulty**: Beginner
**Estimated Time**: 45 minutes
**Focus**: Network security / Packet analysis
**Tools Required**: tshark (CLI packet analyzer), curl

## Prerequisites

- Basic understanding of HTTP and web applications
- tshark installed on your system (part of the Wireshark package)
- Familiarity with network protocols (TCP/IP basics)
- Understanding of client-server communication

## Learning Objectives

By completing this lab, you will:
1. Understand the difference between HTTP and HTTPS
2. Download and analyze PCAP files using tshark on the command line
3. Apply display filters to isolate specific traffic
4. Extract cleartext credentials from HTTP POST requests
5. Follow HTTP streams to see complete conversations
6. Recognize why encryption is mandatory for authentication systems
7. Identify HIPAA compliance violations in healthcare systems

## Background

### HTTP vs HTTPS: The Critical Difference

**HTTP (Hypertext Transfer Protocol)**:
- Transmits data in **cleartext** (unencrypted)
- Anyone on the network path can read the data
- Uses port 80 by default
- Vulnerable to eavesdropping, man-in-the-middle attacks
- **Should NEVER be used for authentication or sensitive data**

**HTTPS (HTTP Secure)**:
- Encrypts data using TLS/SSL
- Protects against eavesdropping and tampering
- Uses port 443 by default
- Required for HIPAA compliance, PCI-DSS, and most security standards
- Free certificates available (Let's Encrypt)

### Why This Matters in Healthcare

- **HIPAA** (Health Insurance Portability and Accountability Act) mandates encryption for Protected Health Information (PHI)
- Cleartext credentials allow unauthorized access to patient records
- Medical systems are high-value targets for attackers
- A single intercepted password can compromise an entire system
- Network sniffing on hospital WiFi or LANs is trivial

### Attack Scenario

1. **Attacker** connects to hospital guest WiFi or compromises a network device
2. **Attacker** runs a packet sniffer (tshark, tcpdump) in promiscuous mode
3. **Legitimate user** logs into legacy HTTP system with their credentials
4. **Attacker** captures the traffic and extracts username/password in cleartext
5. **Attacker** uses stolen credentials to access patient records
6. **Result**: HIPAA breach, patient data exposure, regulatory fines

## Installing tshark

### Linux
```bash
# Debian/Ubuntu
sudo apt update
sudo apt install tshark

# During installation, select "Yes" to allow non-root users to capture packets
# Add your user to the wireshark group
sudo usermod -aG wireshark $USER

# Log out and back in for group changes to take effect

# RHEL/CentOS/Fedora
sudo yum install wireshark-cli
# or
sudo dnf install wireshark-cli
```

### macOS
```bash
# Using Homebrew
brew install wireshark

# tshark is included with the Wireshark package
```

### Windows
Download the installer from [https://www.wireshark.org/download.html](https://www.wireshark.org/download.html). tshark is included and available in the install directory.

## Step-by-Step Solution

### Step 1: Download the Packet Capture

The PCAP file is available on the lab server:

```bash
# Download the capture file
curl http://10.100.{user_id}.10/capture.pcap -o capture.pcap

# Verify download
ls -lh capture.pcap
```

**Expected output**:
```
-rw-r--r-- 1 user user 15K Jan 04 10:30 capture.pcap
```

### Step 2: Open the PCAP with tshark

Use tshark to read and display all packets in the capture file:

```bash
tshark -r capture.pcap
```

This prints a summary of every packet with columns for packet number, time, source, destination, protocol, length, and info.

### Step 3: Understand the tshark Output

When tshark reads a PCAP, each line represents one packet. A typical line looks like:

```
  1   0.000000 192.168.100.50 -> 10.100.1.10  HTTP 350 POST /api/login HTTP/1.1
```

The columns are:
- **Packet number** - Sequential ID for each packet
- **Time** - Relative timestamp from the start of capture
- **Source** - Source IP address
- **Destination** - Destination IP address
- **Protocol** - Detected protocol (TCP, HTTP, TLS, DNS, etc.)
- **Length** - Packet size in bytes
- **Info** - Protocol-specific summary

To get a protocol hierarchy overview showing all protocols in the capture:

```bash
tshark -r capture.pcap -q -z io,phs
```

### Step 4: Apply Display Filter for HTTP

Use the `-Y` flag to apply a display filter and show only HTTP packets:

```bash
tshark -r capture.pcap -Y "http"
```

**What happens**:
- Only HTTP packets are displayed
- Other protocols (DNS, TLS, TCP) are hidden
- You will see a reduced set of packets compared to the full capture

**What you'll see**:
- HTTP GET requests (e.g., GET /, GET /patients)
- HTTP POST requests (e.g., POST /api/login)
- HTTP responses (200 OK, 404 Not Found, etc.)

### Step 5: Filter for HTTP POST Requests

POST requests typically contain form data, including login credentials.

**Refined filter**:
```bash
tshark -r capture.pcap -Y 'http.request.method == "POST"'
```

**Expected result**:
- Should show 1-2 POST request packets
- Info column shows "POST /api/login HTTP/1.1" or similar
- These are the most interesting packets for finding credentials

### Step 6: Examine the POST Request Packet

Extract the detailed fields from the HTTP POST packet using tshark field extraction:

```bash
tshark -r capture.pcap -Y 'http.request.method == "POST"' \
  -T fields -e http.request.method -e http.request.uri -e http.host \
  -e http.content_type -e http.file_data
```

**Expected output** (fields separated by tabs):
```
POST	/api/login	medical.medicare.local	application/x-www-form-urlencoded	username=dr.johnson&password=OCR{http_cr3d3nt14ls}
```

To see the full verbose packet decode (similar to expanding all protocol layers), use the `-V` flag:

```bash
tshark -r capture.pcap -Y 'http.request.method == "POST"' -V
```

This produces output including:

```
Hypertext Transfer Protocol
    POST /api/login HTTP/1.1
    Request Method: POST
    Request URI: /api/login
    Request Version: HTTP/1.1
    Host: medical.medicare.local
    User-Agent: Mozilla/5.0...
    Content-Type: application/x-www-form-urlencoded
    Content-Length: 56
    [Full request URI: http://medical.medicare.local/api/login]
    File Data: 56 bytes
       Line-based text data: application/x-www-form-urlencoded
         username=dr.johnson&password=OCR{http_cr3d3nt14ls}
```

**The flag is in the password field**: `OCR{http_cr3d3nt14ls}`

### Step 7: Alternative Method - Follow HTTP Stream

This method shows the complete HTTP conversation in a readable format.

First, identify the TCP stream index of the HTTP POST packet:

```bash
tshark -r capture.pcap -Y 'http.request.method == "POST"' -T fields -e tcp.stream
```

This outputs the stream number (e.g., `0`). Then follow that stream:

```bash
tshark -r capture.pcap -q -z follow,tcp,ascii,0
```

(Replace `0` with the stream number from the previous command.)

**What you'll see in the stream**:

```
POST /api/login HTTP/1.1
Host: medical.medicare.local
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Accept: application/json, text/plain, */*
Content-Type: application/x-www-form-urlencoded
Content-Length: 56
Connection: keep-alive

username=dr.johnson&password=OCR{http_cr3d3nt14ls}

HTTP/1.1 200 OK
Server: nginx/1.18.0
Content-Type: application/json
Content-Length: 45
Connection: keep-alive

{"status":"success","message":"Login successful"}
```

**The credentials are in plaintext**:
- **Username**: dr.johnson
- **Password**: OCR{http_cr3d3nt14ls}; **This is the flag**

### Step 8: Compare with HTTPS Traffic

**Apply filter for TLS/HTTPS**:
```bash
tshark -r capture.pcap -Y "tls"
```

**What you'll notice**:
- TLS Client Hello and Server Hello are visible (handshake)
- Application Data is **encrypted** (looks like random bytes)
- You **cannot** read the contents of HTTPS traffic
- This demonstrates why HTTPS protects credentials

**Try to follow a TLS stream**:

First get a TLS stream index:
```bash
tshark -r capture.pcap -Y "tls" -T fields -e tcp.stream | head -1
```

Then follow it:
```bash
tshark -r capture.pcap -q -z follow,tcp,ascii,<stream_number>
```

You'll see encrypted gibberish, not readable text. This is what secure communication looks like.

## Understanding the Vulnerability

### What We Found

**Evidence**:
- **System**: Medical records portal at medical.medicare.local
- **Protocol**: HTTP (port 80) - unencrypted
- **Endpoint**: POST /api/login
- **Method**: Form-based authentication
- **Credentials exposed**:
  - Username: dr.johnson
  - Password: OCR{http_cr3d3nt14ls}
- **Compliance**: HIPAA violation (PHI system without encryption)

### Why This Is Critical

**Attack vectors**:
1. **WiFi eavesdropping**: Anyone on the same WiFi can capture this traffic
2. **Network taps**: Attacker with physical access to network can intercept
3. **Compromised router**: Malicious router logs all HTTP traffic
4. **Man-in-the-middle**: ARP spoofing, DNS poisoning enable credential theft
5. **Insider threat**: Network administrators can capture all HTTP credentials

**Impact**:
- Unauthorized access to patient medical records
- Privacy breach affecting potentially thousands of patients
- HIPAA penalties: $100-$50,000 per violation, up to $1.5M annually
- Reputation damage and loss of patient trust
- Potential identity theft and medical fraud

## Display Filter Syntax Reference

These display filters work identically in tshark (`-Y` flag). For example: `tshark -r capture.pcap -Y "<filter>"`

### Basic Filters

| Filter | Description |
|--------|-------------|
| `http` | Show only HTTP traffic |
| `https` or `tls` | Show only HTTPS/TLS traffic |
| `tcp` | Show only TCP traffic |
| `udp` | Show only UDP traffic |
| `dns` | Show only DNS traffic |
| `ip.addr == 10.1.1.1` | Show traffic to/from specific IP |
| `tcp.port == 80` | Show traffic on port 80 |

### HTTP-Specific Filters

| Filter | Description |
|--------|-------------|
| `http.request` | Show only HTTP requests |
| `http.response` | Show only HTTP responses |
| `http.request.method == "GET"` | Show only GET requests |
| `http.request.method == "POST"` | Show only POST requests |
| `http.request.uri contains "login"` | Show requests to URIs containing "login" |
| `http.host == "example.com"` | Show requests to specific host |
| `http.cookie` | Show requests/responses with cookies |

### Search for Keywords

| Filter | tshark Command |
|--------|----------------|
| `http contains "password"` | `tshark -r capture.pcap -Y 'http contains "password"'` |
| `http contains "username"` | `tshark -r capture.pcap -Y 'http contains "username"'` |
| `http.request.uri contains "api"` | `tshark -r capture.pcap -Y 'http.request.uri contains "api"'` |
| `frame contains "OCR{"` | `tshark -r capture.pcap -Y 'frame contains "OCR{"'` |

### Combining Filters

| Filter | Description |
|--------|-------------|
| `http.request.method == "POST" and http contains "password"` | POST requests with password |
| `ip.src == 192.168.1.5 and http` | HTTP from specific source IP |
| `http and not tcp.port == 443` | HTTP but not HTTPS (port 443) |

## Common Mistakes and Troubleshooting

### Mistake 1: Not Filtering Traffic

**Problem**: Scrolling through all packets manually (hundreds of packets).

**Solution**: Always use display filters to narrow down relevant traffic:
```bash
tshark -r capture.pcap -Y 'http.request.method == "POST"'
```

### Mistake 2: Missing the Credentials

**Problem**: Looking in the wrong place for credentials.

**Where credentials are located**:
- In field extraction: Use `-T fields -e http.file_data` to extract POST body data
- In stream output: In the POST body after headers (use `-z follow,tcp,ascii,<stream>`)
- In verbose decode: Visible in the `-V` output under "Line-based text data"

**Search method using tshark**:
```bash
tshark -r capture.pcap -Y 'frame contains "password"'
```

### Mistake 3: Confusing HTTP with HTTPS

**HTTP** (unencrypted):
- Protocol column shows "HTTP"
- Port is usually 80
- Data is readable in cleartext

**HTTPS** (encrypted):
- Protocol column shows "TLS" or "TCP" (encrypted application data)
- Port is usually 443
- Data appears as encrypted bytes

### Mistake 4: Not Using Follow Stream

**Problem**: Trying to manually reconstruct the conversation from individual packets.

**Solution**: Use tshark to follow the TCP stream:
```bash
# Find the stream index for the packet of interest
tshark -r capture.pcap -Y 'http.request.method == "POST"' -T fields -e tcp.stream

# Follow that stream (replace 0 with the actual stream number)
tshark -r capture.pcap -q -z follow,tcp,ascii,0
```

This shows the complete request and response, is much easier to read than individual packets, and automatically reassembles fragmented data.

## Defensive Recommendations

### Immediate Actions

**For this vulnerable system**:
1. **Take the HTTP portal offline immediately**
2. **Deploy HTTPS-only version with valid TLS certificate**
3. **Force all HTTP (port 80) traffic to redirect to HTTPS (port 443)**
4. **Rotate all user passwords** (assume all credentials compromised)
5. **Audit access logs** for unauthorized access using captured credentials
6. **Document incident** for HIPAA breach notification assessment

### Long-Term Security Measures

**Network security**:
- **Implement network segmentation** - Separate medical systems from guest WiFi
- **Deploy NIDS/NIPS** (Network Intrusion Detection/Prevention Systems)
- **Enable TLS inspection** on firewalls for outbound traffic analysis
- **Monitor for cleartext credentials** with automated tools
- **Use 802.1X** for network access control on sensitive segments

**Application security**:
- **Enforce HTTPS everywhere** - No exceptions for authentication
- **Implement HSTS** (HTTP Strict Transport Security) headers
- **Use modern TLS versions** - TLS 1.2 minimum, prefer TLS 1.3
- **Deploy certificate pinning** for mobile apps
- **Conduct regular security audits** and penetration testing

**Compliance**:
- **HIPAA Security Rule** - Encryption in transit and at rest
- **PCI-DSS** - Encryption of cardholder data transmission
- **SOC 2** - Security controls for data transmission
- **GDPR** - Appropriate security measures for personal data

## Real-World Application

### Automated Detection

Security teams don't manually analyze PCAPs for every login. Detection is automated:

**SIEM Rule Example** (Splunk, QRadar, ArcSight):
```
rule detect_cleartext_auth {
  meta:
    description = "Detect cleartext authentication over HTTP"
    severity = "critical"

  condition:
    http.request.method == "POST" and
    http.request.uri contains "login" or "auth" or "signin" and
    not tls.encrypted and
    form_data contains "password"

  action:
    alert("Cleartext authentication detected", source_ip, dest_ip)
    create_ticket()
    block_connection()
}
```

**Intrusion Detection System** (Snort/Suricata):
```
alert tcp any any -> any 80 (msg:"Cleartext Password Transmission";
  content:"POST"; http_method;
  content:"password="; http_client_body;
  classtype:policy-violation;
  sid:1000001;
  rev:1;)
```

### Professional Packet Analysis Workflow

**1. Capture** (tcpdump, tshark):
```bash
# Capture traffic on interface eth0
sudo tcpdump -i eth0 -w capture.pcap

# Capture only HTTP traffic (port 80) using tshark
sudo tshark -i eth0 -f "port 80" -w http_capture.pcap
```

**2. Filter** (tshark):
```bash
# Extract only HTTP traffic from large capture
tshark -r capture.pcap -Y "http" -w http_only.pcap

# Extract credentials from HTTP POST
tshark -r capture.pcap -Y "http.request.method == POST" -T fields -e http.file_data
```

**3. Analyze** (tshark, scripting):
```bash
# Export HTTP objects (files, form data)
tshark -r capture.pcap --export-objects http,./http_objects/

# Generate statistics
tshark -r capture.pcap -q -z http,tree
```

**4. Report**:
- Document findings with command output
- Include PCAP as evidence
- Provide remediation recommendations
- Estimate risk and impact

### Incident Response: Cleartext Credential Exposure

**Phase 1: Identification** (What happened?)
- Cleartext HTTP authentication detected on medical.medicare.local
- Credentials: dr.johnson / OCR{http_cr3d3nt14ls}
- Date/Time: [from packet timestamps]
- Duration: Unknown (need to check historical logs)

**Phase 2: Containment** (Stop the bleeding)
- Immediately disable HTTP portal
- Block port 80 on firewall for this system
- Disable compromised account (dr.johnson)
- Enable logging on all access attempts

**Phase 3: Eradication** (Fix the vulnerability)
- Deploy HTTPS-only version with TLS certificate
- Remove HTTP listener entirely
- Update DNS to point to HTTPS endpoint
- Test authentication over HTTPS

**Phase 4: Recovery** (Return to normal)
- Re-enable service with HTTPS only
- Create new account for dr.johnson with MFA
- Notify user to use new credentials
- Monitor for suspicious access

**Phase 5: Lessons Learned** (Prevent recurrence)
- Add SIEM rule to detect cleartext auth
- Conduct security review of all web applications
- Implement mandatory HTTPS policy
- Schedule quarterly vulnerability assessments
- Train developers on secure coding practices

## Advanced Analysis Techniques

### Extracting All HTTP Credentials

Use tshark to batch-extract credentials from large captures:

```bash
# Extract all HTTP POST bodies
tshark -r capture.pcap -Y "http.request.method == POST" \
  -T fields -e http.file_data | grep -E "(username|password)"

# Extract specific form fields
tshark -r capture.pcap -Y "http.request.method == POST" \
  -T fields -e http.request.uri -e http.file_data
```

### Scripted Analysis

**Python with Scapy**:
```python
from scapy.all import *

def extract_http_credentials(pcap_file):
    packets = rdpcap(pcap_file)
    credentials = []

    for packet in packets:
        if packet.haslayer(Raw):
            load = packet[Raw].load.decode('utf-8', errors='ignore')
            if 'POST' in load and 'password=' in load:
                credentials.append(load)

    return credentials

# Usage
creds = extract_http_credentials('capture.pcap')
for cred in creds:
    print(cred)
```

### Timeline Analysis

```bash
# Create timeline of HTTP requests
tshark -r capture.pcap -Y "http.request" \
  -T fields -e frame.time -e ip.src -e http.request.method -e http.request.uri

# Output:
# Jan 04, 2024 10:15:30.123 192.168.100.50 GET /
# Jan 04, 2024 10:15:32.456 192.168.100.50 GET /patients
# Jan 04, 2024 10:15:35.789 192.168.100.50 POST /api/login
```

## Key Takeaways

### Critical Security Lessons

- **HTTPS is mandatory** - Not optional for any authentication or sensitive data
- **Cleartext = Compromised** - Assume all HTTP credentials are captured
- **Network is hostile** - WiFi, LANs, ISPs can all intercept traffic
- **Encryption in transit** - Required by HIPAA, PCI-DSS, GDPR, SOC 2
- **Defense in depth** - Network security + application security + monitoring

### Packet Analysis Skills Acquired

- Download and analyze PCAP files using tshark on the command line
- Apply display filters to isolate protocols
- Use stream following to see complete conversations
- Extract credentials from HTTP POST requests
- Differentiate encrypted (HTTPS) from cleartext (HTTP) traffic
- Understand packet structure and protocol layers

### Professional Competencies

- Identify security vulnerabilities in network traffic
- Document evidence for incident reports
- Provide actionable remediation recommendations
- Understand compliance requirements (HIPAA encryption mandates)
- Use industry-standard tools (tshark) for security analysis

## Additional Resources

### tshark / Wireshark Learning
- [tshark Man Page](https://www.wireshark.org/docs/man-pages/tshark.html)
- [Wireshark Display Filter Reference](https://www.wireshark.org/docs/dfref/)
- [Wireshark Sample Captures](https://wiki.wireshark.org/SampleCaptures)
- [Wireshark User's Guide](https://www.wireshark.org/docs/wsug_html/)

### Network Security
- [OWASP Transport Layer Protection Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [NIST SP 800-52: Guidelines for TLS Implementations](https://csrc.nist.gov/publications/detail/sp/800-52/rev-2/final)
- [SSL Labs Best Practices](https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices)

### HIPAA Compliance
- [HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [HIPAA Encryption Requirements](https://www.hhs.gov/hipaa/for-professionals/faq/2001/is-the-use-of-encryption-mandatory-in-the-security-rule/index.html)

### Practice
- [Malware-Traffic-Analysis.net](https://www.malware-traffic-analysis.net/) - Practice PCAPs
- [PacketTotal](https://packettotal.com/) - Online PCAP analysis
- [CloudShark](https://www.cloudshark.org/captures) - Public packet captures

## Conclusion

You've successfully:
- Downloaded and analyzed a packet capture file
- Applied tshark display filters to isolate HTTP traffic
- Found and extracted cleartext credentials from HTTP POST
- Understood why HTTPS is critical for authentication systems
- Documented a HIPAA compliance violation
- Learned professional packet analysis techniques

**Flag**: `OCR{http_cr3d3nt14ls}`

**Core Skill Acquired**: Network packet analysis for security assessment - a critical capability for SOC analysts, incident responders, and penetration testers.

**Remember**: If you can see it in tshark over HTTP, so can an attacker. Always use HTTPS for authentication and sensitive data. There are no excuses - free TLS certificates are available, and the security impact of cleartext transmission is well-documented and catastrophic.

Note: If a GUI is available, Wireshark can also open this PCAP for visual analysis.
