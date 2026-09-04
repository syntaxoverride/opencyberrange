# Exercise 2.2: SMTP Email Analysis

## Before You Begin

Exercise 2.1 introduced the SSH-plus-tshark workflow for protocol-specific PCAP
analysis. this exercise applies the same approach to SMTP; the protocol that
carries email traffic.

Make sure you have:

- [ ] Completed Exercise 2.1 (FTP Credential Extraction)
- [ ] VPN connected and verified
- [ ] tshark installed on your local machine (`tshark --version`)
- [ ] SSH client available in your terminal

---

## Scenario

MediCare Regional Hospital's Data Loss Prevention (DLP) system flagged an
outbound email containing keywords associated with patient data. Email
exfiltration by insiders is one of the most common data breach vectors ; 
employees with legitimate access send sensitive data to external accounts,
bypassing traditional perimeter defenses. Your task is to analyze the captured
SMTP traffic, identify the suspicious email, and determine what data was being
sent externally.

---

## Your Objectives

- SSH into the analyst workstation and obtain the PCAP
- Identify all SMTP senders and recipients in the capture
- Isolate emails being sent to external addresses
- Reconstruct the suspicious email and extract its contents
- Find and submit the flag

---

## Background: SMTP and Email Exfiltration

SMTP (Simple Mail Transfer Protocol) is the protocol used to send email. Like
FTP, unencrypted SMTP transmits everything in cleartext; sender addresses,
recipient addresses, subjects, and full message bodies are all visible to
anyone capturing the traffic.

Key SMTP commands:

- **MAIL FROM**: declares the sender's email address
- **RCPT TO**: declares the recipient's email address
- **DATA**: signals that the email body follows

Red flags for exfiltration include: an internal account sending to an external
recipient (Gmail, ProtonMail, Yahoo), sensitive keywords in the subject line,
and a privileged account sending data outside normal communication patterns.

---

## Tool Primer: SMTP Display Filters in tshark

| Filter | What It Shows |
|--------|---------------|
| `smtp` | All SMTP traffic |
| `smtp.req.command == "MAIL"` | Sender addresses (MAIL FROM) |
| `smtp.req.command == "RCPT"` | Recipient addresses (RCPT TO) |
| `smtp.req.command == "DATA"` | Start of email body |
| `smtp contains "keyword"` | SMTP packets containing a specific string |

---

## Walkthrough

### Step 1: Launch the Exercise and Note Your Target IP

Start the lab from the OpenCyberRange platform and note the target IP address
displayed on the launch page.

### Step 2: SSH into the Analyst Workstation and Obtain the PCAP

!!! kali "Connect to the analyst workstation"
    Replace `<target_ip>` with the address shown on the launch page. The SSH session runs from your Kali terminal.

    ```bash
    ssh analyst@<target_ip>
    ```

    When prompted, enter the password: `MediCare2024#`.

If you prefer to analyze the file on your local machine, SCP it separately.

!!! kali "Copy the capture to Kali (optional)"
    Run this from a fresh Kali terminal, not from inside the SSH session. The file lands in your current directory.

    ```bash
    scp analyst@<target_ip>:/home/analyst/captures/email-exfiltration.pcap .
    ```

### Step 3: Get a Protocol Overview

!!! target "Get protocol and conversation overviews"
    Run these on the analyst workstation. The protocol hierarchy confirms SMTP is present, and the TCP conversation summary shows who is communicating with whom.

    ```bash
    tshark -r captures/email-exfiltration.pcap -q -z io,phs
    tshark -r captures/email-exfiltration.pcap -q -z conv,tcp
    ```

    Confirm that SMTP traffic is present before moving on.

### Step 4: List All SMTP Senders and Recipients

!!! target "List all SMTP packets"
    Run this on the analyst workstation. The broad `smtp` filter shows every SMTP packet with its source and destination so you can see the scope of email traffic.

    ```bash
    tshark -r captures/email-exfiltration.pcap -Y "smtp" \
      -T fields -e frame.number -e ip.src -e ip.dst
    ```

    Use this to gauge how many distinct conversations you are dealing with.

!!! target "Extract sender addresses (MAIL FROM)"
    Run this on the analyst workstation. The filter pulls the sender declared in each MAIL FROM command.

    ```bash
    tshark -r captures/email-exfiltration.pcap \
      -Y 'smtp.req.command == "MAIL"' -T fields -e smtp.req.parameter
    ```

    Record each sender address you see.

!!! target "Extract recipient addresses (RCPT TO)"
    Run this on the analyst workstation. The filter pulls the recipient declared in each RCPT TO command along with the source IP.

    ```bash
    tshark -r captures/email-exfiltration.pcap \
      -Y 'smtp.req.command == "RCPT"' \
      -T fields -e frame.number -e ip.src -e smtp.req.parameter
    ```

    You should see several `@medicare.local` addresses, which are legitimate internal emails that act as noise you need to filter through.

---

**Record Your Findings**

| Sender | Recipient |
|--------|-----------|
| | |
| | |
| | |
| | |
| | |

---

### Step 5: Identify External Recipients

!!! target "Exclude internal recipients"
    Run this on the analyst workstation. Piping the RCPT TO output through `grep -v` drops every internal recipient so the external one stands out.

    ```bash
    tshark -r captures/email-exfiltration.pcap \
      -Y 'smtp.req.command == "RCPT"' \
      -T fields -e frame.number -e ip.src -e smtp.req.parameter \
      | grep -v medicare.local
    ```

    The `grep -v medicare.local` filter reveals the one external recipient.

You can also search for known external providers directly.

!!! target "Search for external mail providers"
    Run this on the analyst workstation. The filter matches any SMTP packet mentioning a common external provider.

    ```bash
    tshark -r captures/email-exfiltration.pcap \
      -Y 'smtp contains "protonmail" || smtp contains "gmail"'
    ```

    A hit on protonmail or gmail confirms an email leaving the organization.

### Step 6: Find the TCP Stream Number for the Suspicious Email

!!! target "Find the suspicious email's TCP stream"
    Run this on the analyst workstation. The stream number ties together every packet in the suspicious email conversation.

    ```bash
    tshark -r captures/email-exfiltration.pcap \
      -Y 'smtp contains "protonmail"' -T fields -e tcp.stream
    ```

    Note the stream number returned; you feed it into the next command.

### Step 7: Follow the Stream to Read the Full Email

!!! target "Reconstruct the full email"
    Run this on the analyst workstation. Replace `<stream>` with the number from Step 6 to reassemble the complete SMTP conversation in readable form.

    ```bash
    tshark -r captures/email-exfiltration.pcap \
      -q -z follow,tcp,ascii,<stream>
    ```

    The output shows the full email exchange including the subject line and message body. Look carefully at the body; it contains a patient data record count, database credentials, and a link to an external file sharing service. The flag is in the credentials.

---

**Record Your Findings**

- Sender: _______________
- Recipient: _______________
- Subject: _______________
- Patient record count mentioned: _______________
- Credentials found in email body: _______________
- Flag: _______________

---

### Step 8: Document the Evidence

Summarize what you found before closing the investigation:

- **What data was exposed:** A database export with patient records, record
  counts, and backup credentials granting further database access.
- **Who sent it:** `dbadmin@medicare.local`: a database administrator with
  privileged access to patient data.
- **Where it was going:** `external.contact@protonmail.com`: an external
  address outside the organization's control.

---

## Analysis Questions

**1. The PCAP contains several legitimate internal emails. How did you filter
them out to find the suspicious one?**

> By piping the RCPT TO output through `grep -v medicare.local` to exclude
> internal recipients. The only email going to an external address
> (protonmail.com) was the suspicious one. In a real investigation, you would
> also check for emails to personal email services, file sharing domains, and
> newly registered domains.

**2. The email was sent from dbadmin@medicare.local. What makes this sender
particularly concerning?**

> A database administrator has privileged access to patient records. An email
> from this account containing database export information, patient record
> counts, and backup credentials suggests either a malicious insider or a
> compromised admin account. Either scenario is a critical security incident.

**3. The email body contained a link to an external file sharing service. What
additional investigation would you perform?**

> Check whether the file sharing URL was accessed from any internal system
> (look for HTTP/HTTPS requests to that domain in the PCAP or proxy logs).
> Attempt to determine what was uploaded. Review the dbadmin account's login
> history and file access logs. Check if the backup_admin credentials in the
> email are still valid.

---

## Key Takeaways

- Unencrypted SMTP exposes email addresses, subjects, and full message bodies
  to anyone capturing traffic
- The RCPT TO command reveals the recipient; external recipients from internal
  accounts are a major red flag
- Following the TCP stream reconstructs the complete email conversation in
  readable form
- Data exfiltration via email is common because email is expected to leave the
  network
- DLP systems detect these incidents by scanning for sensitive keywords in
  outbound email

---

*Next: Exercise 2.3; HTTP Session Hijacking*
