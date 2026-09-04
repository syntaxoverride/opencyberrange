# Exercise 2.1: FTP Credential Extraction

## Before You Begin

Exercise 2.1 is the first exercise in Chapter N2 (PCAP Forensics). The workflow here differs
from Chapter N1. Instead of downloading log files with `curl`, you SSH into an
analyst workstation where the packet capture is already staged. You then use
tshark; the command-line version of Wireshark; to dissect the traffic directly
from the terminal. If you completed Exercise 1.2, you already have the basics of
tshark. this exercise builds on that foundation with protocol-specific filtering.

Make sure you have:

- [ ] Completed all Chapter N1 labs
- [ ] VPN connected and verified
- [ ] tshark installed on your local machine (`tshark --version`)
- [ ] SSH client available in your terminal

---

## Scenario

MediCare Regional Hospital's intrusion detection system has flagged unusual FTP
activity on the medical records server. FTP transmits credentials in cleartext,
meaning anyone who captures the network traffic can read usernames and passwords
directly from the packets. The IDS alert suggests that unauthorized access may
have occurred. Your task is to analyze the captured traffic, extract any
credentials transmitted over FTP, and determine what data the attacker accessed
after authentication.

---

## Your Objectives

- SSH into the analyst workstation and locate the PCAP file
- Use tshark to identify FTP authentication traffic in the capture
- Extract credentials from FTP USER and PASS commands
- Determine whether the login attempt succeeded or failed
- Identify what files were accessed after authentication
- Find and submit the flag

---

## Background: Why FTP Is Dangerous

FTP (File Transfer Protocol) dates from 1971 (RFC 114) and transmits everything
in cleartext; usernames, passwords, commands, and file contents. Unlike SFTP,
which tunnels through SSH, FTP has no encryption layer. Anyone capturing network
traffic between the client and server can read FTP credentials directly from the
packets, exactly as they were typed.

In healthcare environments, using FTP to transfer patient data is a compliance
violation under HIPAA, which requires encryption for protected health information
(PHI) in transit. Despite this, legacy FTP servers remain common in organizations
that have not modernized their file transfer infrastructure.

---

## Tool Primer: FTP Display Filters in tshark

Since this is the first protocol-specific tshark lab, the table below lists the
display filters you will use throughout the walkthrough.

| Filter | What It Shows |
|--------|---------------|
| `ftp` | All FTP control channel traffic |
| `ftp.request.command == "USER"` | Username commands sent by the client |
| `ftp.request.command == "PASS"` | Password commands sent by the client |
| `ftp.request.command == "RETR"` | File download (retrieve) commands |
| `ftp.response.code == 230` | Successful login responses |
| `ftp.response.code == 530` | Failed login responses |

FTP response codes follow a pattern: codes beginning with 2 indicate success,
codes beginning with 5 indicate permanent failure. The two you care about most
during credential analysis are 230 (User logged in) and 530 (Login incorrect).

---

## Walkthrough

### Step 1: Launch the Exercise and Note Your Target IP

Start the lab from the OpenCyberRange platform and note the target IP address
displayed on the launch page.

### Step 2: SSH into the Analyst Workstation

!!! kali "Connect to the analyst workstation"
    Replace `<target_ip>` with the address shown on the launch page. The SSH session runs from your Kali terminal and lands you on the staged analyst host.

    ```bash
    ssh analyst@<target_ip>
    ```

    When prompted, enter the password: `MediCare2024#`. You should land in the `/home/analyst` directory.

### Step 3: Locate the PCAP File

!!! target "Confirm the packet capture is staged"
    Run this on the analyst workstation after the SSH session connects. The listing verifies the capture file is present before you begin analysis.

    ```bash
    ls -lh /home/analyst/captures/
    ```

    You should see `medical-records-ftp.pcap` in the listing.

If you prefer to analyze the file on your local Kali machine, SCP it from a
separate terminal.

!!! kali "Copy the capture to Kali (optional)"
    Run this from a fresh Kali terminal, not from inside the SSH session. The file lands in your current directory for local analysis.

    ```bash
    scp analyst@<target_ip>:/home/analyst/captures/medical-records-ftp.pcap .
    ```

    For this walkthrough, all remaining commands run directly on the analyst workstation.

### Step 4: Get a Protocol Overview

!!! target "Get a protocol hierarchy overview"
    Run this on the analyst workstation. The protocol hierarchy statistics (`io,phs`) show a breakdown of every protocol in the PCAP by packet count and byte volume.

    ```bash
    tshark -r captures/medical-records-ftp.pcap -q -z io,phs
    ```

    Look for `ftp` in the output to confirm that FTP control channel traffic is present.

### Step 5: Find the Successful Login

!!! target "Filter for the successful login response"
    Run this on the analyst workstation. The filter isolates the FTP response code that indicates a successful authentication.

    ```bash
    tshark -r captures/medical-records-ftp.pcap -Y "ftp.response.code == 230" \
      -T fields -e frame.number -e ftp.response.arg
    ```

    The `ftp.response.code == 230` filter captures packets where the server responded with code 230 (User logged in) and displays the frame number and response text.

---

**Record Your Findings**

- Frame number of the 230 response: _______________
- Response text returned by the server: _______________

---

### Step 6: Extract the Credentials

!!! target "Extract every credential pair"
    Run this on the analyst workstation. The filter pulls every USER and PASS command transmitted in the capture so you can read the cleartext credentials.

    ```bash
    tshark -r captures/medical-records-ftp.pcap \
      -Y 'ftp.request.command == "USER" || ftp.request.command == "PASS"' \
      -T fields -e frame.number -e ftp.request.command -e ftp.request.arg
    ```

    The output shows multiple USER/PASS pairs. Most are followed by 530 (failed login) responses. One pair succeeded. Identify the credentials that preceded the 230 response you found in Step 5.

---

**Record Your Findings**

- Successful username: _______________
- Successful password (flag): _______________

| Frame | Command | Argument | Result |
|-------|---------|----------|--------|
| | USER | | 530 (failed) |
| | PASS | | 530 (failed) |
| | USER | | 230 (success) |
| | PASS | | 230 (success) |

---

### Step 7: Follow the TCP Stream

To see the complete FTP conversation; including what the attacker did after
logging in; follow the TCP stream that contains the successful login.

!!! target "Find the TCP stream for the successful login"
    Run this on the analyst workstation. The stream number ties together every packet in the successful FTP conversation.

    ```bash
    tshark -r captures/medical-records-ftp.pcap -Y "ftp.response.code == 230" \
      -T fields -e tcp.stream
    ```

    Note the stream number returned; you feed it into the next command.

!!! target "Reconstruct the full FTP conversation"
    Run this on the analyst workstation. Replace `<stream>` with the number from the previous command to reassemble the entire conversation in readable form.

    ```bash
    tshark -r captures/medical-records-ftp.pcap -q -z follow,tcp,ascii,<stream>
    ```

    In the output, look for the `RETR` command, which tells you what file the attacker downloaded. The file `patient_records.db` confirms data exfiltration from the medical records server.

---

## Analysis Questions

**1. The PCAP contains several failed login attempts before the successful one.
What usernames were tried, and what do they tell you about the attacker?**

> The failed attempts used common/default usernames; admin, root, test, backup,
> and ftp; all returning response code 530. The pattern is consistent with a
> brute-force dictionary attack or automated scanning. The successful login used
> "medrecords," which is specific to this system, suggesting the attacker had
> prior knowledge of the target or performed reconnaissance beforehand.

**2. After logging in, the attacker downloaded `patient_records.db`. How would
you find all files accessed using tshark?**

> Filter for the RETR command: `tshark -r captures/medical-records-ftp.pcap -Y 'ftp.request.command == "RETR"' -T fields -e ftp.request.arg`. The filter displays the
> filename for every RETR (file retrieval) command. You can also check for `STOR`
> (upload), `LIST` (directory listing), and `DELE` (delete) to build a complete
> picture of the attacker's activity.

**3. What protocol should replace FTP for transferring sensitive files?**

??? note "Reveal Answer"

    SFTP (SSH File Transfer Protocol) or SCP (Secure Copy). Both encrypt the
    entire session including credentials and file contents. FTPS (FTP over TLS)
    is another option but less commonly deployed. In healthcare, HIPAA requires
    encryption in transit for protected health information; unencrypted FTP is a
    compliance violation regardless of whether an attacker is present.

---

## Key Takeaways

- FTP transmits credentials and file contents in cleartext; a single packet
  capture reveals everything, including usernames, passwords, and transferred
  data
- Response code 230 means successful login; 530 means failure; filter on these
  codes to find what matters quickly and skip the noise
- The tshark workflow you used here (protocol overview, broad filter, narrow
  filter, stream follow) works for analyzing any protocol, not just FTP
- Always investigate what the attacker did after authentication, not just the
  credentials themselves; the RETR command revealed data exfiltration
- SFTP or SCP should replace FTP wherever sensitive data is involved, especially
  in environments subject to compliance requirements like HIPAA

---

*Next: Exercise 2.2; SMTP Email Analysis*
