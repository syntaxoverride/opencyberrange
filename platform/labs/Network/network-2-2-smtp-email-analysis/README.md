# SMTP Email Content Analysis - Walkthrough

## Lab Overview

Investigate a data exfiltration incident by analyzing SMTP email traffic. Learn to reconstruct complete emails from packet captures and identify sensitive data being sent via unencrypted email.

**Difficulty**: Intermediate
**Estimated Time**: 45-60 minutes
**Focus**: SMTP protocol, email forensics, data exfiltration detection

> **Note:** If a GUI is available, Wireshark can also open this PCAP for visual analysis.

## Prerequisites

- Network Level 1 labs completed
- Network 2-1 (FTP Credential Extraction) completed
- Familiarity with tshark (the command-line packet analyzer)
- Understanding of email protocols

## Learning Objectives

1. Analyze SMTP protocol traffic
2. Reconstruct email messages from packet captures
3. Identify data exfiltration via email
4. Extract email headers, body, and metadata
5. Understand email encryption importance

## Scenario

MediCare's DLP system flagged an outbound email containing patient data keywords. You must analyze the network capture to determine what was sent and to whom.

## Step-by-Step Solution

### Step 1: SSH to Analyst Workstation

```bash
ssh analyst@10.100.{user_id}.10
Password: MediCare2024#
```

### Step 2: Download the PCAP

```bash
scp analyst@10.100.{user_id}.10:/home/analyst/captures/email-exfiltration.pcap .
```

### Step 3: Get a Protocol Overview

Start by examining the protocol hierarchy to understand what traffic the capture contains:

```bash
tshark -r captures/email-exfiltration.pcap -q -z io,phs
```

This displays a breakdown of all protocols in the PCAP, including the volume of SMTP traffic.

You can also review the TCP conversations to see which hosts communicated on port 25:

```bash
tshark -r captures/email-exfiltration.pcap -q -z conv,tcp
```

### Step 4: Filter for SMTP Traffic

List all SMTP packets with their source and destination addresses:

```bash
tshark -r captures/email-exfiltration.pcap -Y "smtp" -T fields -e frame.number -e ip.src -e ip.dst
```

You'll see several email conversations spanning 3-4 hours.

### Step 5: Identify Suspicious Email

Look for red flags:
- **External recipients** (not @medicare.local)
- **Suspicious subjects** (confidential, database, export)
- **DATA commands** followed by email content

First, find all senders:

```bash
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "MAIL"' -T fields -e smtp.req.parameter
```

Next, find all recipients:

```bash
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "RCPT"' -T fields -e frame.number -e ip.src -e smtp.req.parameter
```

Now filter for external recipients; anyone not at the internal medicare.local domain:

```bash
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "RCPT"' -T fields -e frame.number -e ip.src -e smtp.req.parameter | grep -v medicare.local
```

You can also search for known external mail providers:

```bash
tshark -r captures/email-exfiltration.pcap -Y 'smtp contains "protonmail" || smtp contains "gmail" || smtp contains "yahoo"' -T fields -e frame.number -e ip.src -e ip.dst
```

### Step 6: Follow the TCP Stream

Once you identify the suspicious traffic involving "protonmail", determine which TCP stream it belongs to:

```bash
tshark -r captures/email-exfiltration.pcap -Y 'smtp contains "protonmail"' -T fields -e tcp.stream
```

This returns a stream number (e.g., `5`). Use that number to follow the entire TCP stream and read the complete SMTP conversation:

```bash
tshark -r captures/email-exfiltration.pcap -q -z follow,tcp,ascii,<stream>
```

Replace `<stream>` with the actual stream number from the previous command.

### Step 7: Extract the Email Content

In the TCP stream output, you'll see the full SMTP conversation:

```
220 mail.medicare.local ESMTP Postfix
EHLO db-admin.local
250-mail.medicare.local
MAIL FROM:<dbadmin@medicare.local>
250 OK
RCPT TO:<external.contact@protonmail.com>    <-- EXTERNAL! Suspicious!
250 OK
DATA
354 End data with <CR><LF>.<CR><LF>
From: dbadmin@medicare.local
To: external.contact@protonmail.com
Subject: Database Export - Confidential    <-- RED FLAG!

Here is the patient database export you requested.

Total records: 15,847 patient files
Includes: Names, DOB, SSN, diagnoses, medications

Access credentials for the backup server:
Username: backup_admin
Password: OCR{smtp_d4t4_3xf1ltr4t10n}    <-- FLAG!

Database dump attached (see file share link)
https://filestorage.external.com/share/Ab7Yx23K

Let me know if you need anything else.

- DB Admin
.
250 OK
```

**Flag**: `OCR{smtp_d4t4_3xf1ltr4t10n}`

## Key Takeaways

### SMTP Security Weaknesses

**Unencrypted SMTP exposes:**
- Sender and recipient email addresses
- Email subject lines
- Complete email body content
- Attachments (if inline or base64 encoded)
- Authentication credentials if SMTP AUTH used

### Email Forensics

**What we extracted:**
- **Sender**: dbadmin@medicare.local
- **Recipient**: external.contact@protonmail.com (EXTERNAL!)
- **Subject**: Database Export - Confidential
- **Content**: Patient database information, credentials, file share link
- **Timestamp**: ~16:15 (2 hours into the 4-hour capture)

### Red Flags for Data Exfiltration

- **External recipient** - Email leaving the organization
- **Suspicious subject** - "Confidential", "Export", "Database"
- **Sensitive content** - Patient records, credentials
- **File sharing links** - External storage service
- **Database admin account** - Privileged user sending data out

## tshark Analysis Techniques

### Useful SMTP Commands

```bash
# Protocol hierarchy overview
tshark -r captures/email-exfiltration.pcap -q -z io,phs

# All SMTP traffic with source/destination
tshark -r captures/email-exfiltration.pcap -Y "smtp" -T fields -e frame.number -e ip.src -e ip.dst

# Find DATA commands (email content)
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "DATA"' -T fields -e frame.number -e ip.src -e ip.dst

# Find recipients
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "RCPT"' -T fields -e frame.number -e ip.src -e smtp.req.parameter

# Find senders
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "MAIL"' -T fields -e smtp.req.parameter

# Search for external domains
tshark -r captures/email-exfiltration.pcap -Y 'smtp contains "gmail" || smtp contains "yahoo" || smtp contains "protonmail"'

# Search for suspicious keywords
tshark -r captures/email-exfiltration.pcap -Y 'smtp contains "password" || smtp contains "confidential"'

# Find external recipients (exclude internal domain)
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "RCPT"' -T fields -e smtp.req.parameter | grep -v medicare.local
```

### Follow TCP Stream Benefits

Using `tshark -q -z follow,tcp,ascii,<stream>`:
- Shows complete SMTP conversation
- Email appears in readable format
- Output can be redirected to a file for further analysis
- Easier than packet-by-packet analysis
- Displays the full command/response flow

### TCP Conversations Summary

To see all TCP conversations and identify which ones use port 25 (SMTP):

```bash
tshark -r captures/email-exfiltration.pcap -q -z conv,tcp
```

This shows source/destination addresses, ports, packet counts, and byte totals for each TCP session.

## Real-World Application

### Incident Response

**Documentation required:**
- Sender email and IP address
- Recipient email (external)
- Timestamp of email
- Email subject and body
- Any attachments or links
- Evidence of what data was exfiltrated

### Immediate Actions

1. **Disable account**: dbadmin@medicare.local
2. **Block recipient**: external.contact@protonmail.com
3. **Investigate file share**: Check what was uploaded
4. **Reset credentials**: backup_admin password compromised
5. **Review access logs**: What else did this account access?

### Long-Term Remediation

**Technical controls:**
- **Enable TLS/STARTTLS**: Encrypt email in transit
- **DLP policies**: Block sensitive data in email
- **Email gateway**: Scan outbound emails
- **Restrict external email**: Require approval for external recipients
- **Monitor database access**: Alert on bulk exports

**Process controls:**
- **Least privilege**: DBAs shouldn't email patient data
- **Data classification**: Mark sensitive emails
- **User training**: Recognize insider threats
- **Incident response plan**: Clear escalation process

## Advanced Analysis

### Extracting Email Attachments

If the email had attachments, they'd appear as:

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="patients.pdf"
Content-Transfer-Encoding: base64

JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PC9MZW5ndGggNiAwIFIvRmlsdGVy... [base64 data]
```

To extract using tshark and standard CLI tools:
1. Follow the TCP stream and redirect to a file:
   ```bash
   tshark -r captures/email-exfiltration.pcap -q -z follow,tcp,ascii,<stream> > smtp_stream.txt
   ```
2. Extract the base64-encoded attachment data from the stream output
3. Decode: `base64 -d attachment_data.b64 > patients.pdf`
4. Open the file for analysis

### Timeline Reconstruction

Using tshark to identify SMTP conversations and their timing:

```bash
# Show TCP conversations with timestamps and byte counts
tshark -r captures/email-exfiltration.pcap -q -z conv,tcp

# Filter for conversations on port 25 specifically
tshark -r captures/email-exfiltration.pcap -Y "tcp.port == 25" -T fields -e frame.time -e ip.src -e ip.dst -e tcp.stream | sort -u -t$'\t' -k4,4
```

Find conversations on port 25, note start times and duration, then correlate with other logs.

### Automated Detection

**tshark command** to find external recipients:
```bash
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "RCPT"' -T fields -e smtp.req.parameter | grep -v medicare.local
```

Output:
```
<external.contact@protonmail.com>
```

## Common Mistakes

### Mistake 1: Focusing on Legitimate Emails

The PCAP contains 4-5 legitimate internal emails. Don't get distracted:
- nurse@medicare.local -> doctor@medicare.local; Internal
- it-admin@medicare.local -> helpdesk@medicare.local; Internal
- dbadmin@medicare.local -> external.contact@protonmail.com; EXTERNAL!

Use the `grep -v medicare.local` pipe to quickly filter out internal mail and focus on external recipients.

### Mistake 2: Not Following the TCP Stream

Trying to read emails packet-by-packet from tshark field output is tedious. Use `tshark -q -z follow,tcp,ascii,<stream>` to see the complete email in one view. First identify the stream number, then follow it.

### Mistake 3: Not Checking Recipients

The subject line is a clue, but the external recipient is the real red flag. Always check RCPT TO commands:

```bash
tshark -r captures/email-exfiltration.pcap -Y 'smtp.req.command == "RCPT"' -T fields -e smtp.req.parameter
```

## Defense Recommendations

### Email Security Best Practices

**Encryption:**
- **TLS/STARTTLS**: Encrypt emails in transit
- **S/MIME or PGP**: End-to-end email encryption
- **Force TLS**: Reject unencrypted connections

**DLP (Data Loss Prevention):**
- Scan outbound emails for sensitive data
- Block PHI, PII, credentials in email body
- Quarantine suspicious emails for review

**Email Gateway:**
- Sandboxing for attachments
- URL analysis for malicious links
- SPF/DKIM/DMARC for authentication

**Monitoring:**
- Log all email traffic
- Alert on external recipients from privileged accounts
- Monitor for bulk email sends
- Track file sharing service usage

## Conclusion

You've successfully:
- Analyzed SMTP protocol traffic using tshark
- Reconstructed complete emails from packet captures
- Identified data exfiltration via email
- Extracted sensitive information and credentials
- Understood email security weaknesses

**Core skill acquired**: Email forensics and data exfiltration detection through command-line packet analysis.

## References

- [SMTP Protocol (RFC 5321)](https://tools.ietf.org/html/rfc5321)
- [tshark Man Page](https://www.wireshark.org/docs/man-pages/tshark.html)
- [Email Security Best Practices (NIST)](https://csrc.nist.gov/publications/detail/sp/800-177/final)
- [Data Exfiltration Detection Techniques](https://www.sans.org/reading-room/whitepapers/detection/detecting-dns-tunneling-34152)
