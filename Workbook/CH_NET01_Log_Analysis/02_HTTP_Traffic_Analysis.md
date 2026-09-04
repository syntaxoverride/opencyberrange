# Exercise 1.2: HTTP Traffic Analysis

## Before You Begin

In Exercise 1.1 you analyzed plain-text firewall logs using grep, awk, and the Unix counting pipeline. this exercise shifts to a different evidence format: a packet capture (PCAP) file. Instead of reading human-readable log lines, you work with recorded network traffic and use tshark to decode it.

tshark is the command-line version of Wireshark. Confirm it is installed before continuing.

!!! kali "Confirm tshark is installed"
    Run the version check from your analyst Kali workstation to confirm the tool is present before downloading the capture.

    ```bash
    tshark --version
    ```

    If the command returns version information, you are ready to proceed. If it is not found, install the `tshark` package through your distribution's package manager before starting the lab.

## Scenario

MediCare Regional Hospital's network monitoring system has flagged cleartext HTTP traffic on a segment that should be using HTTPS exclusively. The alert points to a medical records portal that appears to be transmitting login credentials without encryption. A packet capture of the suspicious session has been saved for analysis.

As the investigating analyst, you need to download the capture, identify the unencrypted traffic, extract whatever credentials were exposed, and determine the scope of the risk.

## Your Objectives

- Download the packet capture file from the target machine.
- Use tshark to identify HTTP traffic within the capture.
- Locate login credentials transmitted in cleartext.
- Understand why HTTP is dangerous for authentication.
- Find and submit the flag.

## Background: HTTP vs HTTPS

HTTP transmits every byte of data in cleartext. When a user submits a login form over HTTP, their username and password travel across the network as readable text. Anyone in a position to capture that traffic; an attacker on the same WiFi network, a compromised router, or a physical network tap; can read the credentials directly.

HTTPS wraps HTTP inside a TLS encryption layer. Even if an attacker captures HTTPS traffic, the payload is encrypted and unreadable without the server's private key. The TLS handshake is visible, but the actual content (login forms, medical records, session tokens) is protected.

In healthcare environments, this distinction carries regulatory weight. HIPAA requires encryption for protected health information (PHI) in transit. A medical records portal running over HTTP is not only a security vulnerability; it is a compliance violation. The capture you are about to analyze demonstrates exactly what an attacker sees when encryption is absent.

## Tool Primer: tshark

Exercise 1.2 is your first exercise using tshark, so take a moment to understand the tool before you begin the walkthrough. tshark is the command-line interface to the Wireshark packet analysis engine. It reads the same PCAP files and supports the same display filter syntax as the Wireshark GUI, but it runs entirely in the terminal.

**Reading a capture file.** The `-r` flag specifies the input file.

```bash
tshark -r capture.pcap
```

**Applying a display filter.** The `-Y` flag filters packets using Wireshark display filter syntax.

```bash
tshark -r capture.pcap -Y "http"
```

**Extracting specific fields.** The `-T fields` option switches to field extraction mode, and each `-e` flag names a field to output. Fields use dot notation.

```bash
tshark -r capture.pcap -T fields -e http.request.method -e http.request.uri
```

**Verbose packet decode.** The `-V` flag prints every protocol layer of each matching packet.

```bash
tshark -r capture.pcap -Y "http" -V
```

**Protocol hierarchy statistics.** The `-q -z io,phs` combination shows a breakdown of all protocols present in the capture without printing individual packets.

```bash
tshark -r capture.pcap -q -z io,phs
```

**Following a TCP stream.** The `-q -z follow,tcp,ascii,<stream>` option reconstructs a full TCP conversation in readable form. The stream number identifies which conversation to follow.

```bash
tshark -r capture.pcap -q -z follow,tcp,ascii,0
```

**Common display filter fields used in this exercise:**

| Filter | Matches |
|--------|---------|
| `http` | All HTTP traffic |
| `http.request.method == "POST"` | HTTP POST requests only |
| `http.file_data` | HTTP message body content |
| `tcp.stream` | TCP stream index number |
| `tls` | All TLS/HTTPS traffic |
| `frame contains "password"` | Any packet containing the string "password" |

## Walkthrough

### Step 1: Launch the Exercise

In the Open Cyber Range interface, navigate to **Network -> Level 1 -> HTTP Traffic Analysis** and start the lab. Wait until the status indicator shows **Running**, then note the target IP displayed on the lab page. You will substitute this value wherever you see `<target_ip>` in the commands below.

### Step 2: Download the Packet Capture

!!! kali "Download the packet capture from the target"
    Pull the PCAP file from the target machine to your local working directory. The `curl` download runs from your Kali workstation so you can analyze the capture offline.

    ```bash
    curl http://<target_ip>/capture.pcap -o capture.pcap
    ```

    You should see a progress bar followed by a confirmation that the file has been saved. If the download fails, verify your VPN connection and confirm the target IP is correct.

### Step 3: Get a Protocol Overview

!!! kali "Print the protocol hierarchy"
    Before diving into specific packets, get a high-level view of what protocols are present in the capture.

    ```bash
    tshark -r capture.pcap -q -z io,phs
    ```

    The `-z io,phs` option prints a protocol hierarchy showing the percentage and byte count for each protocol layer. Look for both HTTP and TLS entries in the output. The presence of both confirms that the capture contains a mix of encrypted and unencrypted web traffic.

### Step 4: Filter for HTTP Traffic

!!! kali "Filter the capture for HTTP packets"
    Narrow the view to HTTP packets only.

    ```bash
    tshark -r capture.pcap -Y "http"
    ```

    The output shows each HTTP packet with its timestamp, source and destination addresses, and a summary of the HTTP layer. You should see GET and POST requests along with their corresponding responses. Note the destination host; this is the medical records portal.

### Step 5: Find POST Requests

!!! kali "Filter for HTTP POST requests"
    Login forms typically submit credentials via HTTP POST. Filter for POST requests specifically.

    ```bash
    tshark -r capture.pcap -Y 'http.request.method == "POST"'
    ```

    The output should show one or more POST requests. These are the packets most likely to contain credentials, because POST is the standard method for form submissions.

---

**Record Your Findings**

From the output of Steps 3 through 5, record the following:

- Protocols present in the capture: _______________
- Number of HTTP packets: _______________
- Number of POST requests: _______________
- Destination host for POST requests: _______________

---

### Step 6: Extract the Credentials

!!! kali "Extract POST request fields"
    Now extract the fields that reveal what was submitted. Use the `-T fields` option with multiple `-e` flags to pull out the request method, URI, host, content type, and body data.

    ```bash
    tshark -r capture.pcap -Y 'http.request.method == "POST"' -T fields -e http.request.method -e http.request.uri -e http.host -e http.content_type -e http.file_data
    ```

    The output displays the extracted fields in tab-separated columns. In the `http.file_data` field, you should see the form data submitted by the user, including a username and password in cleartext.

!!! kali "Verbose decode of the POST packet"
    If you want to see the full packet decode for additional context, use verbose mode.

    ```bash
    tshark -r capture.pcap -Y 'http.request.method == "POST"' -V
    ```

    The `-V` verbose mode prints every protocol layer of the POST packet, from Ethernet through HTTP. Scroll through the output to find the HTTP form data section containing the submitted credentials.

### Step 7: Follow the TCP Stream

To see the complete HTTP conversation; the request and the server's response together; follow the TCP stream that contains the POST request.

!!! kali "Find the TCP stream number"
    First, find the stream number for the POST request.

    ```bash
    tshark -r capture.pcap -Y 'http.request.method == "POST"' -T fields -e tcp.stream
    ```

!!! kali "Reconstruct the full TCP conversation"
    Then use that stream number (for example, `0`) to follow the full conversation.

    ```bash
    tshark -r capture.pcap -q -z follow,tcp,ascii,0
    ```

    The `follow,tcp,ascii` option reconstructs the entire TCP session in ASCII. You see the client's HTTP request (including headers and the POST body) followed by the server's HTTP response. The credentials are clearly visible in the request body:

```
username=dr.johnson&password=OCR{<flag_here>}
```

The flag is in `OCR{<flag_here>}` format.

---

**Record Your Findings**

- Username found in the POST data: _______________
- Password found in the POST data: _______________
- Flag: _______________
- What URI was the POST submitted to: _______________
- Was the server's response visible in the TCP stream: _______________

---

## Analysis Questions

Work through these questions to deepen your understanding of the techniques used in this exercise.

**1. The capture also contains TLS traffic. What happens when you try to read that traffic with tshark?**

??? note "Reveal Answer"

    TLS traffic appears as encrypted application data. You can see the TLS handshake messages (Client Hello, Server Hello, Certificate) but the actual content is unreadable. Running `tshark -r capture.pcap -Y "tls"` shows the encrypted records without any way to extract usernames, passwords, or page content. Encryption is exactly the protection that HTTP lacks.

**2. A hospital administrator argues that the portal is on an "internal network" so HTTP is safe. Why is this wrong?**

??? note "Reveal Answer"

    Internal networks are not immune to eavesdropping. Insider threats, compromised workstations, and lateral movement by attackers all happen inside the network perimeter. An attacker who gains access to any device on the same network segment can capture traffic with tools like tcpdump or Wireshark. HIPAA requires encryption for protected health information regardless of whether the network is internal or external. The argument that "internal means safe" is a misconception that has contributed to many real-world breaches.

**3. What tshark display filter would you use to find all packets containing the word "password"?**

??? note "Reveal Answer"

    `tshark -r capture.pcap -Y 'frame contains "password"'`: the `frame contains` filter searches the raw bytes of every packet for the specified string. The filter works across all protocol layers, catching passwords in HTTP form data, URL parameters, or any other part of the packet payload.

## Key Takeaways

- HTTP transmits everything in cleartext; credentials, session tokens, and data are all visible to anyone capturing traffic on the network path.
- tshark uses the same display filter syntax as Wireshark, making skills transferable between the command line and the GUI.
- The `-T fields -e` option extracts specific protocol fields for clean, scriptable output.
- Following a TCP stream with `-q -z follow,tcp,ascii,<stream>` shows the complete client-server conversation in readable form.
- HTTPS/TLS makes captured traffic unreadable, which is why encryption is mandatory for any system handling authentication or sensitive data.
- In regulated environments like healthcare, transmitting credentials over HTTP is both a security vulnerability and a compliance violation.
