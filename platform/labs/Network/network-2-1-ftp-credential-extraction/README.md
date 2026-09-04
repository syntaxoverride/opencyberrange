# FTP Credential Extraction - Walkthrough

## Lab Overview

This intermediate-level lab teaches packet capture analysis by having you SSH into a network analyst workstation, download a real-world PCAP file, and extract FTP credentials from captured traffic. The PCAP contains 2-3 hours of realistic hospital network traffic with multiple protocols.

**Difficulty**: Intermediate
**Estimated Time**: 45-60 minutes
**Focus**: tshark/command-line analysis, FTP protocol, credential extraction

> **Note**: If a GUI is available, Wireshark can also open this PCAP for visual analysis.

## Prerequisites

- Completion of Network Level 1 labs
- Basic tshark/packet analysis knowledge
- Understanding of TCP/IP
- SSH client installed

## Learning Objectives

1. SSH into remote analyst workstation
2. Transfer PCAP files for analysis
3. Filter large packet captures for relevant traffic using tshark
4. Understand FTP protocol authentication
5. Extract cleartext credentials from FTP sessions
6. Recognize protocol security weaknesses

## Scenario

You're analyzing captured traffic from MediCare's medical records server. The IDS flagged unusual FTP activity, and you need to determine what credentials were used to access sensitive patient data.

## Step-by-Step Solution

### Step 1: SSH to Analyst Workstation

```bash
ssh analyst@10.100.{user_id}.10
Password: MediCare2024#
```

### Step 2: Verify PCAP File Exists

```bash
ls -lh /home/analyst/captures/
```

You should see `medical-records-ftp.pcap` (several MB).

### Step 3: Download PCAP to Your Kali Machine

```bash
# From your Kali terminal (not SSH session)
scp analyst@10.100.{user_id}.10:/home/analyst/captures/medical-records-ftp.pcap .
# Enter password: MediCare2024#
```

### Step 4: Get a Protocol Overview with tshark

Use tshark to get a protocol hierarchy summary of the capture:

```bash
tshark -r captures/medical-records-ftp.pcap -q -z io,phs
```

**What you'll see**:
- Hundreds of packets across multiple protocols
- Protocol breakdown including DNS, HTTP, FTP, TCP
- Traffic spanning 2-3 hours

This gives you a bird's-eye view of the capture before diving into specific protocols.

### Step 5: Filter for FTP Traffic

Use tshark to display only FTP control channel traffic (port 21), with key fields extracted:

```bash
tshark -r captures/medical-records-ftp.pcap -Y "ftp" -T fields -e frame.number -e ip.src -e ip.dst -e ftp.request.command -e ftp.request.arg -e ftp.response.code -e ftp.response.arg
```

This outputs a table of all FTP commands and responses with frame numbers, source/destination IPs, commands, arguments, and response codes.

### Step 6: Find Successful Login

Filter for FTP response code 230 ("User logged in, proceed"):

```bash
tshark -r captures/medical-records-ftp.pcap -Y "ftp.response.code == 230" -T fields -e frame.number -e ftp.response.arg
```

You should see 1-2 lines of output showing the successful login response and its frame number.

### Step 7: Extract Credentials (Method 1 - Direct Field Extraction)

Extract all USER and PASS commands from the capture to see every login attempt:

```bash
tshark -r captures/medical-records-ftp.pcap -Y 'ftp.request.command == "USER" || ftp.request.command == "PASS"' -T fields -e frame.number -e ftp.request.command -e ftp.request.arg
```

In the output, you will see multiple failed login attempts (from usernames like admin, root, test, backup, ftp, guest) before the successful one. Look for:
- `USER medrecords` - The username
- `PASS OCR{ftp_us3r_p4ssw0rd_l34k}` - The password (FLAG!)

### Step 8: Extract Credentials (Method 2 - Follow the TCP Stream)

This approach shows the complete FTP conversation in context. First, identify the TCP stream index for the successful session by finding a packet from it (e.g., the frame with the 230 response):

```bash
tshark -r captures/medical-records-ftp.pcap -Y "ftp.response.code == 230" -T fields -e tcp.stream
```

Note the stream number returned (e.g., `5`), then reconstruct the full conversation:

```bash
tshark -r captures/medical-records-ftp.pcap -q -z follow,tcp,ascii,5
```

(Replace `5` with the actual stream number from the previous command.)

This displays the entire FTP session in readable ASCII:

```
220 MediCare Medical Records FTP Server Ready
USER medrecords
331 Password required for medrecords
PASS OCR{ftp_us3r_p4ssw0rd_l34k}
230 User medrecords logged in
LIST
150 Opening data connection for directory list
RETR patient_records.db
150 Opening BINARY mode data connection for patient_records.db
```

The password is the flag: **OCR{ftp_us3r_p4ssw0rd_l34k}**

## Key Takeaways

### FTP Security Weaknesses

**Why FTP is dangerous**:
- All commands transmitted in cleartext
- Usernames and passwords visible in packet captures
- File contents unencrypted
- No modern authentication (no 2FA, no key-based auth)

### Failed vs. Successful Logins

**Failed attempts (distractors in PCAP)**:
- Usernames: admin, root, test, backup, ftp, guest
- Response: `530 Login incorrect`
- These are noise - focus on finding 230 responses

**Successful attempt**:
- Username: medrecords
- Password: OCR{ftp_us3r_p4ssw0rd_l34k}
- Response: `230 User logged in`

### tshark Analysis Skills

**Essential filters learned**:
- `ftp` - All FTP traffic
- `ftp.response.code == 230` - Successful logins
- `ftp.request.command == "USER"` - Username commands
- `ftp.request.command == "PASS"` - Password commands
- `ftp.request.command == "RETR"` - File downloads

**Workflow**:
1. Get a protocol overview (`-q -z io,phs`)
2. Apply broad filter (`-Y "ftp"`)
3. Narrow to specific events (`-Y "ftp.response.code == 230"`)
4. Work backwards to find credentials (`-Y 'ftp.request.command == "USER" || ftp.request.command == "PASS"'`)
5. Use TCP stream follow for full context (`-q -z follow,tcp,ascii,<stream>`)

## Common Mistakes

### Mistake 1: Not Downloading the PCAP

You cannot analyze the PCAP while SSH'd into the workstation (unless tshark is installed there). The typical workflow is:
1. SSH to workstation
2. SCP the file to your Kali machine
3. Analyze with tshark on Kali

### Mistake 2: Looking at Failed Attempts

The PCAP contains multiple failed logins (admin, root, test, etc.) with response `530 Login incorrect`. These are distractors.

Focus on finding `230 User logged in`.

### Mistake 3: Not Using TCP Stream Follow

Manually finding USER and PASS commands works, but `tshark -q -z follow,tcp,ascii,<stream>` makes it much easier to see the entire conversation at once.

### Mistake 4: Wrong Display Filter Syntax

**Wrong**: `ftp == 230`
**Right**: `ftp.response.code == 230`

Display filters need correct field names. This applies to both tshark `-Y` filters and Wireshark display filters; the syntax is identical.

## Real-World Application

### Why This Matters

In real incident response:
- Network traffic captures are critical evidence
- Credentials in cleartext indicate protocol misuse
- FTP should be replaced with SFTP (SSH File Transfer Protocol)
- This type of analysis identifies:
  - What data was accessed
  - Who accessed it (credentials used)
  - When it happened (timestamps)
  - What was downloaded (file names)

### Incident Response Steps

1. **Identify**: Found credentials medrecords / OCR{ftp_us3r_p4ssw0rd_l34k}
2. **Document**: Username, password, timestamp, files accessed
3. **Contain**: Disable compromised account immediately
4. **Investigate**: Check if credentials used elsewhere
5. **Remediate**: Force password change, disable FTP, migrate to SFTP
6. **Report**: Document findings for CISO, compliance team

### Defensive Recommendations

**Immediate actions**:
- Disable the FTP service
- Reset the medrecords account password
- Check logs for other uses of these credentials
- Notify affected users/systems

**Long-term fixes**:
- Replace FTP with SFTP (encrypted)
- Implement certificate-based authentication
- Use VPN for file transfers
- Enable MFA on all file access systems
- Monitor for cleartext protocols (FTP, Telnet, HTTP with passwords)

## Advanced Analysis

### Extracting Transferred Files

FTP uses a separate data connection for file transfers. To see what was downloaded:

```bash
tshark -r captures/medical-records-ftp.pcap -Y 'ftp.request.command == "RETR"' -T fields -e ftp.request.arg
```

This reveals the file name: `patient_records.db`.

To investigate the data connection further, look for FTP-DATA packets:

```bash
tshark -r captures/medical-records-ftp.pcap -Y "ftp-data" -T fields -e frame.number -e ip.src -e ip.dst -e data.len
```

**In this PCAP**: The data connection may not be fully captured, but you can confirm the command was issued and identify the file name.

### Timeline Reconstruction

Use tshark's conversation statistics to reconstruct the session timeline:

```bash
tshark -r captures/medical-records-ftp.pcap -q -z conv,tcp
```

This shows all TCP conversations including the FTP session (port 21). Note the start time, duration, number of packets, and bytes transferred. Correlate this information with IDS alerts or other logs to build a complete picture.

For a time-based breakdown of traffic:

```bash
tshark -r captures/medical-records-ftp.pcap -q -z io,stat,60
```

This shows packet counts per 60-second interval across the entire capture.

### Automating Detection

**tshark one-liner** to extract all FTP passwords from any capture:
```bash
tshark -r captures/medical-records-ftp.pcap -Y 'ftp.request.command == "PASS"' -T fields -e ftp.request.arg
```

Output:
```
OCR{ftp_us3r_p4ssw0rd_l34k}
```

**Combined extraction** of all login attempts with results:
```bash
tshark -r captures/medical-records-ftp.pcap -Y 'ftp.request.command == "USER" || ftp.request.command == "PASS" || ftp.response.code == 230 || ftp.response.code == 530' -T fields -e frame.number -e ftp.request.command -e ftp.request.arg -e ftp.response.code -e ftp.response.arg
```

## tshark Quick Reference

### Display Filter Syntax (used with -Y flag)

```
# All FTP
ftp

# Specific commands
ftp.request.command == "USER"
ftp.request.command == "PASS"
ftp.request.command == "RETR"

# Specific responses
ftp.response.code == 230   # Login success
ftp.response.code == 530   # Login failed
ftp.response.code == 150   # File transfer starting

# Combined filters
(ftp.request.command == "USER") || (ftp.request.command == "PASS")
```

### Useful tshark Options

| Option | Purpose | Example |
|--------|---------|---------|
| `-r <file>` | Read a PCAP file | `tshark -r capture.pcap` |
| `-Y <filter>` | Apply display filter | `tshark -r cap.pcap -Y "ftp"` |
| `-T fields` | Output specific fields | `tshark -T fields -e ip.src` |
| `-e <field>` | Specify field to extract | `-e ftp.request.command` |
| `-q -z io,phs` | Protocol hierarchy stats | `tshark -r cap.pcap -q -z io,phs` |
| `-q -z conv,tcp` | TCP conversation list | `tshark -r cap.pcap -q -z conv,tcp` |
| `-q -z follow,tcp,ascii,N` | Follow TCP stream N | `tshark -r cap.pcap -q -z follow,tcp,ascii,0` |
| `-q -z io,stat,N` | I/O stats per N seconds | `tshark -r cap.pcap -q -z io,stat,60` |

## Conclusion

You've successfully:
- SSH'd into a network analyst workstation
- Downloaded a real-world PCAP file
- Filtered traffic in a large capture using tshark
- Extracted FTP credentials from cleartext traffic
- Understood FTP protocol security weaknesses

**Core skill acquired**: Command-line packet capture analysis for incident response and forensics.

## References

- [tshark Man Page](https://www.wireshark.org/docs/man-pages/tshark.html)
- [Wireshark Display Filter Reference](https://www.wireshark.org/docs/dfref/)
- [FTP Protocol (RFC 959)](https://tools.ietf.org/html/rfc959)
- [SANS: Network Forensics with Wireshark](https://www.sans.org/blog/a-quick-practical-reference-for-tcpdump/)
- [Wireshark/tshark User's Guide](https://www.wireshark.org/docs/wsug_html_chunked/)
