# Exercise 2.5: Attack Chain Analysis

## Before You Begin

Exercise 2.5 is the capstone lab of Chapter N2. You will use every skill from the previous four labs; HTTP analysis, SMTP investigation, session tracking, DNS detection, and FTP credential extraction; combined into a single multi-stage attack investigation. The PCAP is larger and more complex than anything you have seen so far. Take your time, work through each stage methodically, and build a complete picture of the attack before moving on.

**Connection Details**

| Field    | Value                |
|----------|----------------------|
| SSH      | `ssh analyst@<target_ip>` |
| Password | `MediCare2024#`      |
| PCAP     | `/home/analyst/captures/full-attack.pcap` |

All analysis in this exercise is performed with `tshark` over SSH. You do not have access to Wireshark.

> **Estimated time:** 60-90 minutes. this exercise is significantly longer than previous labs. You may want to keep a text file open to organize your notes as you work through each stage.

## Scenario

MediCare's SOC detected suspicious outbound traffic from the patient records department late on a Friday evening. Initial triage revealed multiple compromised systems and unusual authentication patterns on the domain controller. The CISO activated the incident response team and escalated the investigation to priority one.

Marcus Thompson, the senior network engineer, captured 5 hours of network traffic from the affected subnet before the systems were isolated. The capture contains the complete attack; from the moment the attacker gained access to the moment they exfiltrated data. Your task is to analyze this traffic and reconstruct the complete attack chain from initial compromise through data exfiltration.

## Your Objectives

- Map all hosts and protocols in the capture
- Identify the initial compromise vector
- Detect command-and-control communication
- Find evidence of credential harvesting
- Track lateral movement to other systems
- Locate the data exfiltration and extract the flag
- Build a complete attack timeline

By the end of this exercise, you will have a complete incident report showing the full scope of the compromise.

## Background: The Cyber Kill Chain

Real-world intrusions rarely happen in a single step. Attackers follow a predictable progression, and each stage leaves distinct network evidence. Understanding this chain helps you know what to look for and where to look next.

1. **Initial Access**: The attacker delivers malware to a victim, often through a malicious download or phishing link. Network evidence includes HTTP requests to suspicious domains and executable file transfers.
2. **Command and Control (C2)**: The malware phones home to an attacker-controlled server, establishing a persistent communication channel. Network evidence includes regular outbound HTTPS connections to unusual domains at fixed intervals (beaconing).
3. **Credential Harvesting**: The attacker uses the compromised host to gather valid credentials for other internal systems. Network evidence includes repeated failed authentication attempts followed by a success.
4. **Lateral Movement**: With stolen credentials, the attacker accesses other systems on the network. Network evidence includes SMB or RDP connections from the compromised host to servers it does not normally contact.
5. **Data Exfiltration**: The attacker transfers stolen data out of the network. Network evidence includes unusual protocols like FTP carrying large transfers to external IP addresses.

Each of these stages is visible in a packet capture. Your job is to find them all.

The key insight is that attackers must use the network to accomplish their goals, and every network action produces packets. Even when traffic is encrypted, metadata like connection timing, destination addresses, and protocol selection reveals the attacker's intent.

## Walkthrough

### Stage 1: Initial Assessment

Before diving into specific attacks, you need to understand what is in the capture. Start with a high-level overview of protocols and hosts. A scope-first overview is the same approach you would take in a real investigation; understand the scope before focusing on details.

!!! target "Generate a protocol hierarchy"
    Run this on the analysis container, which you reach with the SSH details at the top of the exercise. The protocol hierarchy tells you which protocols to investigate.

    ```bash
    tshark -r captures/full-attack.pcap -q -z io,phs
    ```

    Look for HTTP, TLS, SMB, and FTP; each corresponds to an attack stage.

!!! target "Examine IP conversations"
    Run this on the analysis container. The IP conversation summary identifies which hosts are communicating and how much data they exchange.

    ```bash
    tshark -r captures/full-attack.pcap -q -z conv,ip
    ```

    Large byte counts between an internal host and an external IP hint at exfiltration.

!!! target "List all endpoints"
    Run this on the analysis container. The endpoint list maps every host that appears in the capture.

    ```bash
    tshark -r captures/full-attack.pcap -q -z endpoints,ip
    ```

    The internal network is `10.0.10.0/24`. Any addresses outside this range are external and deserve scrutiny. Pay attention to the byte counts in the conversation output; large transfers to external IPs may indicate exfiltration.

Take note of key internal hosts. In this network, `10.0.10.5` is the domain controller, `10.0.10.50` is the file server, and workstations occupy the rest of the subnet. Knowing the role of each host helps you interpret the traffic patterns in later stages.

---

**Record Your Findings**

- What protocols are present in the capture?
- Which internal hosts appear most active?
- Which external IP addresses do you see?
- What is the internal network range?
- Can you identify the roles of the key internal hosts?

---

### Stage 2: Initial Access

With the network mapped, investigate how the attacker gained their initial foothold. HTTP traffic is unencrypted, so you can see the full request details including the domain, URI path, and filename. Look at HTTP requests to find suspicious downloads.

!!! target "List all HTTP GET requests"
    Run this on the analysis container. The filter lists every HTTP GET with its timestamp, source, destination, host, and URI.

    ```bash
    tshark -r captures/full-attack.pcap -Y 'http.request.method == "GET"' -T fields -e frame.time -e ip.src -e ip.dst -e http.host -e http.request.uri
    ```

    Review the output for anything unusual; executable downloads, connections to suspicious domains, or requests to uncommon TLDs.

Narrow your search to executable file downloads specifically.

!!! target "Find executable downloads"
    Run this on the analysis container. The filter matches any request whose URI contains `.exe`, which surfaces malware delivery.

    ```bash
    tshark -r captures/full-attack.pcap -Y 'http.request.uri contains ".exe"' -T fields -e frame.time -e ip.src -e ip.dst -e http.host -e http.request.uri
    ```

    You should see an internal host downloading an executable from a domain that does not belong to MediCare. The download marks the initial compromise: the victim at `10.0.10.25` downloaded `system-update.exe` from `malicious-cdn.tk`: malware disguised as a legitimate update.

Note the `.tk` top-level domain. The `.tk` TLD offers free domain registration and is disproportionately used for malicious purposes. Seeing an executable download from a `.tk` domain is a strong indicator of compromise.

---

**Record Your Findings**

- Which internal host downloaded the file? (victim IP)
- What domain served the file?
- What was the filename?
- At what time offset did this occur?

---

### Stage 3: Command and Control

After the malware was executed, it needed to establish communication with the attacker. Without a C2 channel, the attacker cannot issue commands or receive data from the compromised host.

C2 traffic is often encrypted with TLS, but the Server Name Indication (SNI) field in the TLS handshake reveals the destination domain. The SNI is sent in cleartext during the handshake, before encryption begins.

!!! target "Extract TLS SNI values"
    Run this on the analysis container. The filter pulls the Server Name Indication from each TLS handshake, revealing the destination domain even though the rest of the session is encrypted.

    ```bash
    tshark -r captures/full-attack.pcap -Y "tls.handshake.extensions_server_name" -T fields -e frame.time -e ip.src -e ip.dst -e tls.handshake.extensions_server_name
    ```

    Look for a domain that appears repeatedly at regular intervals. A beaconing pattern (the same host connecting to the same external domain every few minutes) is a hallmark of C2 communication. Legitimate HTTPS traffic does not follow such rigid timing.

Note the interval between connections. Malware authors configure a beacon interval to balance responsiveness with stealth. A 5-minute interval is common because it blends into normal traffic volume while still allowing the attacker to issue commands promptly.

To calculate the beacon interval, compare the timestamps of consecutive connections to the C2 domain. If you see connections at roughly 5-minute intervals, this confirms automated beaconing rather than human-initiated browsing. You can also count the total number of beacons to estimate how long the C2 channel was active.

---

**Record Your Findings**

- What is the C2 domain?
- How often does the compromised host beacon? (interval)
- How many C2 connections do you observe?
- When did C2 communication begin relative to the initial download?

---

### Stage 4: Credential Harvesting

With a C2 channel established, the attacker begins probing for credentials to move deeper into the network. The compromised workstation alone is not the attacker's goal; they need credentials to access more valuable systems like file servers and databases. Look for SMB authentication attempts against the domain controller.

!!! target "Extract SMB2 session setup attempts"
    Run this on the analysis container. The filter pulls SMB2 Session Setup requests along with the status code that records whether each authentication succeeded or failed.

    ```bash
    tshark -r captures/full-attack.pcap -Y "smb2.cmd == 1" -T fields -e frame.time -e ip.src -e ip.dst -e smb2.nt_status
    ```

    SMB2 command 1 is Session Setup; the authentication request. The `nt_status` field tells you whether each attempt succeeded or failed. A status of `0x00000000` means success; any other value is a failure.

A pattern of many failures followed by a success is a brute-force attack. The attacker tried multiple username and password combinations against the domain controller until one worked. Count the failed and successful attempts to understand the scope of the attack.

In a real investigation, you would also correlate the successful authentication with the account name to determine which credentials were compromised. The domain controller at `10.0.10.5` is a high-value target because domain admin credentials grant access to every system on the network.

---

**Record Your Findings**

- How many failed authentication attempts do you see?
- How many successful authentications followed?
- What is the target system? (domain controller IP)
- At what time offset did the brute force begin?

---

### Stage 5: Lateral Movement

Armed with valid credentials, the attacker pivots from the initially compromised host to access other systems on the internal network. The pivot is lateral movement; the attacker expands their footprint beyond the single compromised workstation. Look for SMB connections from the victim to new targets.

!!! target "Track SMB traffic from the compromised host"
    Run this on the analysis container. The filter scopes the capture to SMB2 traffic leaving the compromised workstation so you can see which new systems it reaches.

    ```bash
    tshark -r captures/full-attack.pcap -Y "ip.src == 10.0.10.25 and smb2" -T fields -e frame.time -e ip.dst -e smb2.cmd
    ```

    You should see the compromised host connecting to a file server that it did not contact before the credential harvesting stage. The SMB commands tell you what the attacker did on that server; tree connects indicate share access, and create/read commands indicate file operations.

The SMB activity is classic lateral movement: the attacker uses the compromised workstation as a stepping stone to reach more valuable targets, in this case the file server at `10.0.10.50` containing patient records.

Compare the timing of this activity with the credential harvesting in Stage 4. Lateral movement should begin shortly after the attacker obtained valid credentials. The timing correlation strengthens your conclusion that the stolen credentials were used to access the file server.

---

**Record Your Findings**

- Which new system did the attacker access?
- What SMB operations were performed?
- What shares or files were accessed?
- At what time offset did lateral movement begin?

---

### Stage 6: Data Exfiltration

The final stage is the attacker's true objective: stealing data. Everything up to this point; the malware download, the C2 channel, the brute-forced credentials, the lateral movement; was preparation for this moment. With access to the file server, the attacker packages the target data and transfers it out of the network.

Look for FTP traffic, which is unusual for a workstation in a healthcare environment.

!!! target "Extract all FTP commands"
    Run this on the analysis container. The broad `ftp` filter shows every FTP command and argument, which is itself suspicious for a healthcare workstation.

    ```bash
    tshark -r captures/full-attack.pcap -Y "ftp" -T fields -e frame.time -e ip.src -e ip.dst -e ftp.request.command -e ftp.request.arg
    ```

    Any outbound FTP from a workstation is a red flag worth investigating.

Then focus specifically on STOR commands, which upload files to the FTP server.

!!! target "Find the uploaded file"
    Run this on the analysis container. The filter isolates STOR commands, which upload files and reveal what the attacker exfiltrated.

    ```bash
    tshark -r captures/full-attack.pcap -Y 'ftp.request.command == "STOR"' -T fields -e ftp.request.arg
    ```

    The filename in the STOR command contains the flag in `OCR{<flag_here>}` format. The attacker uploaded the file to the external FTP server at `198.51.100.42`: a clear case of data exfiltration.

Note that the attacker chose FTP, an unencrypted protocol. Choosing FTP is a common mistake by attackers; FTP transmits filenames, credentials, and data in cleartext, making it trivially detectable. More sophisticated attackers use encrypted channels such as HTTPS or DNS tunneling to exfiltrate data.

---

**Record Your Findings**

- What is the external FTP server IP?
- What filename was uploaded?
- What is the flag?
- What FTP credentials were used?
- At what time offset did exfiltration occur?
- How large was the transferred file?

---

### Complete Attack Timeline

After working through all six stages, assemble your findings into a single timeline. The completed timeline is the deliverable you would present to the incident response team.

| Time   | Stage               | Activity                        | Source       | Destination          |
|--------|----------------------|---------------------------------|--------------|----------------------|
| T+0    | Capture Start        | Traffic recording begins        |;            |;                    |
| T+30   | Initial Access       | Downloaded system-update.exe    | 10.0.10.25   | malicious-cdn.tk     |
| T+45   | C2 Setup             | First beacon to C2 server       | 10.0.10.25   | c2-server.tk         |
| T+90   | Credential Harvest   | SMB brute force against DC      | 10.0.10.25   | 10.0.10.5 (DC)       |
| T+120  | Lateral Movement     | SMB connection to file server   | 10.0.10.25   | 10.0.10.50           |
| T+180  | Data Exfiltration    | FTP upload of patient records   | 10.0.10.25   | 198.51.100.42        |

The timeline shows the entire attack chain from initial compromise to data theft in 3 hours. Every stage was visible in the packet capture, and every stage represented a detection opportunity that was missed.

In an incident response report, this timeline is one of the most valuable deliverables. It allows the security team to understand the scope and speed of the attack, identify which systems and accounts were affected, and determine what defensive controls failed at each stage.

## Analysis Questions

**Question 1.** The attack took 3 hours from initial access to data exfiltration. At which stage could the earliest detection have occurred, and how?

??? note "Reveal Answer"

    Stage 2 (Initial Access); the HTTP download of `system-update.exe` from `malicious-cdn.tk` could have been caught by a web proxy or DNS filtering service blocking known-malicious domains. The `.tk` TLD is frequently associated with malicious activity and is often blocked by default in enterprise environments. Alternatively, Stage 3 (C2) could have been detected by monitoring for HTTPS connections to suspicious TLDs with regular beaconing intervals. Either detection would have prevented the subsequent credential harvesting, lateral movement, and exfiltration.

**Question 2.** The attacker used FTP to exfiltrate data. Why is this unusual for a workstation, and what controls would have caught it?

??? note "Reveal Answer"

    Normal workstations do not use FTP. An outbound FTP connection from a desktop PC to an external IP address is highly anomalous. A network-based anomaly detection system or a firewall rule blocking outbound FTP from workstation subnets would have prevented the exfiltration entirely. Even a simple egress filtering policy that only allows HTTP, HTTPS, and DNS from workstation VLANs would have stopped this stage of the attack.

**Question 3.** How would you use the IOCs from this analysis to protect other systems on the network?

??? note "Reveal Answer"

    Block the domains (`malicious-cdn.tk`, `c2-server.tk`) in DNS filtering and proxy blacklists. Block the external IP addresses (`198.51.100.42` and the C2 server IP) at the perimeter firewall. Search all systems for the file `system-update.exe` using endpoint tools. Check all workstations for HTTPS connections to the C2 domain in proxy logs. Reset credentials for any accounts that were accessed from the compromised host `10.0.10.25`. Deploy endpoint detection and response (EDR) agents across the environment to detect similar malware and lateral movement in the future.

## Key Takeaways

- Real attacks follow a predictable chain: access, command and control, credentials, lateral movement, and exfiltration. Recognizing this pattern helps you investigate efficiently.
- Each stage leaves distinct network evidence that `tshark` can detect; HTTP downloads, TLS beaconing, SMB authentication failures, and FTP uploads all tell part of the story.
- The protocol hierarchy overview is always the first step in any PCAP investigation. It tells you what protocols are present and guides your analysis.
- Building a timeline is critical for incident response. It shows the progression of the attack and identifies the earliest point where detection could have interrupted the chain.
- this exercise combined HTTP, TLS, SMB, and FTP analysis; all skills from the previous four labs. In real incident response, you will use these techniques together, not in isolation.
- Documenting indicators of compromise (IOCs); domains, IPs, filenames, and behavioral patterns; enables your organization to detect the same attacker targeting other systems.
