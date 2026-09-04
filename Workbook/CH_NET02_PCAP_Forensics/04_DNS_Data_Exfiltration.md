# Exercise 2.4: DNS Data Exfiltration

## Before You Begin

Exercise 1.3 detected DNS anomalies in text-based logs. The current exercise takes DNS analysis further; instead of just identifying suspicious domains, you extract and decode data that was smuggled out through DNS queries. The key difference is the decode pipeline (`tshark` to `cut` to `tr` to `xxd`) that converts raw packet captures into readable stolen data. The decode pipeline is new and specific to this exercise.

You should be comfortable using `tshark` display filters and field extraction from the previous labs. The new skill here is chaining multiple command-line tools together to transform raw network data into human-readable output.

All analysis is performed via `tshark` over SSH. There is no Wireshark GUI available in this environment.

## Scenario

MediCare's network monitoring system flagged a spike in DNS query volume from a billing department workstation. The alert triggered at 3:00 AM; well outside normal business hours for the billing department.

DNS queries normally fly under the radar because firewalls never block them; every host on every network needs DNS to function. Marcus, the senior analyst, suspects DNS tunneling; a technique where attackers encode stolen data into DNS subdomain queries and send them to an attacker-controlled domain. The queries look legitimate on the surface, but the subdomains carry chunks of encoded information.

If confirmed, this means patient data left the network through a channel that no firewall or proxy would have caught. For a healthcare organization handling protected health information, that constitutes a HIPAA breach with mandatory reporting requirements.

## Your Objectives

- SSH into the analysis container
- Identify the suspicious domain receiving high query volume
- Analyze the subdomain structure for signs of encoded data
- Extract and decode the exfiltrated data
- Determine what information was stolen
- Find and submit the flag

## Background: DNS Tunneling

To understand DNS tunneling, you first need to understand what normal DNS traffic looks like.

Normal DNS traffic consists of short, recognizable domain names queried sporadically. A user visits `mail.google.com`, their browser queries DNS, and the resolver returns an IP address. The domain names are human-readable, the queries are infrequent, and no meaningful data travels in the query itself. A typical workstation might generate a few hundred DNS queries per hour, spread across many different domains.

DNS tunneling inverts this model. Instead of querying real domain names, the attacker's malware encodes stolen data into the subdomain portion of a DNS query. Each query carries a small chunk of hex-encoded data as a subdomain, sent to an attacker-controlled domain:

```
4a6f686e20446f65.data-exfil.tk
3132332d34352d36.data-exfil.tk
37383920444f4220.data-exfil.tk
```

The attacker registers a domain (like `data-exfil.tk`) and runs an authoritative DNS server for it. Every query for `*.data-exfil.tk` reaches that server. The attacker collects the subdomains from each query and reassembles the hex data into the original stolen content.

The encoding matters. Raw binary data or ASCII text cannot appear directly in a domain name; DNS labels have strict character restrictions. Hex encoding converts each byte of stolen data into two hexadecimal characters (0-9, a-f), which are valid in domain names. The trade-off is that each query can only carry a limited amount of data (DNS labels are capped at 63 characters), so the attacker must split the payload across many queries.

DNS tunneling works because DNS is almost never blocked. Firewalls allow it. Proxies ignore it. Most security tools do not inspect the content of DNS queries.

Detection indicators include:

- **High query volume**: A single host sending 50 or more queries to a single domain in a short period
- **Long subdomains**: Random-looking strings of hex or base64 characters where you would expect human-readable hostnames
- **Unusual TLDs**: Free or inexpensive TLDs such as `.tk`, `.xyz`, `.top`, `.ml`, or `.ga` that attackers favor for disposable infrastructure
- **Rapid-fire timing**: Queries arriving in quick succession with uniform intervals, suggesting automated generation
- **Single source**: One IP address generating the bulk of the suspicious traffic

this exercise differs from Exercise 1.3 in a critical way. Exercise 1.3 identified the anomaly; a suspicious domain with high query counts. Here, you go further: you extract the encoded subdomains from the packet capture and decode them to reveal exactly what data was stolen.

## Walkthrough

### Step 1: Launch the Exercise

Start the lab environment from the OpenCyberRange launcher. Wait for the container status to show as running before proceeding. this exercise uses a single container that provides SSH access to the analysis environment.

### Step 2: SSH into the Container

!!! kali "Connect to the analysis container"
    Run this from your Kali terminal. Replace `<target_ip>` with the address shown on the launch page. When prompted, enter the password `MediCare2024#`.

    ```bash
    ssh analyst@<target_ip>
    ```

    You now have a shell on the analysis host.

!!! target "Confirm the capture file is present"
    Run this on the analysis container after the SSH session connects. The listing verifies the PCAP is staged before you start.

    ```bash
    ls -la captures/dns-tunnel.pcap
    ```

    The file `~/captures/dns-tunnel.pcap` contains the network traffic captured from the billing department network segment during the time window identified by the monitoring alert.

### Step 3: Get a Protocol Overview

!!! target "Get a protocol hierarchy overview"
    Run this on the analysis container. The `tshark -z io,phs` command displays a protocol hierarchy showing the byte and packet counts for each protocol in the capture.

    ```bash
    tshark -r captures/dns-tunnel.pcap -q -z io,phs
    ```

    The protocol hierarchy guides where to look next. You should see that DNS dominates the traffic. A capture that is overwhelmingly DNS; with very little HTTP, TLS, or other application traffic; is already unusual. In a normal network capture, you would expect a mix of protocols. A capture dominated by DNS suggests automated or programmatic query generation rather than organic browsing.

### Step 4: List DNS Queries and Count by Domain

!!! target "List all DNS queries"
    Run this on the analysis container. The filter `dns.flags.response == 0` selects only DNS queries (not responses). The `-T fields` option outputs tab-separated values, and the `-e` flags specify which fields to include: frame number, source IP, and the queried domain name.

    ```bash
    tshark -r captures/dns-tunnel.pcap -Y "dns.flags.response == 0" -T fields -e frame.number -e ip.src -e dns.qry.name
    ```

    The output shows every outbound DNS query with its source IP and the domain name being queried.

To identify which domains receive the most queries, count by base domain.

!!! target "Count queries by base domain"
    Run this on the analysis container. The `rev | cut | rev` pipeline reverses each domain name, extracts the last two fields (which become the base domain), reverses it back, and counts occurrences.

    ```bash
    tshark -r captures/dns-tunnel.pcap -Y "dns.flags.response == 0" -T fields -e dns.qry.name | rev | cut -d. -f1-2 | rev | sort | uniq -c | sort -rn | head -20
    ```

    The `sort -rn` flag sorts numerically in descending order, so the domains with the highest query counts appear first.

---

**Record Your Findings**

- What are the top queried domains in the capture?
- Which domain stands out with 50 or more queries?
- Is that query volume normal for a single domain from a single workstation?
- What TLD does the suspicious domain use, and is it commonly associated with legitimate services?

---

### Step 5: Filter for the Suspicious Domain

Look at the output from the previous command. The domain `data-exfil.tk` stands out with an unusually high query count; far more than any legitimate domain in the capture. The `.tk` TLD (Tokelau) is a free domain registration service that attackers frequently use for disposable infrastructure.

!!! target "Filter for the suspicious domain"
    Run this on the analysis container. The filter narrows the capture to queries for the suspicious domain so you can inspect their subdomains.

    ```bash
    tshark -r captures/dns-tunnel.pcap -Y 'dns.qry.name contains "data-exfil.tk"' -T fields -e frame.number -e ip.src -e dns.qry.name
    ```

    Note the source IP address; all queries originate from a single host (`10.0.2.45`). The host `10.0.2.45` is the billing department workstation identified in the alert.

Examine the subdomain portions of each query carefully. They do not look like normal hostnames such as `www`, `mail`, or `api`. Instead, they appear to be long strings of hexadecimal characters (0-9, a-f). The hexadecimal subdomains are a strong indicator that data is being encoded into the DNS queries.

### Step 6: Check for Long Query Names

Another indicator of DNS tunneling is unusually long domain names. Normal queries like `www.google.com` are around 15 characters. DNS tunneling queries often exceed 50 characters because the hex-encoded data payload inflates the subdomain.

!!! target "Filter for unusually long query names"
    Run this on the analysis container. The filter selects queries whose name exceeds 50 characters, a length normal hostnames rarely reach.

    ```bash
    tshark -r captures/dns-tunnel.pcap -Y "dns.qry.name.len > 50" -T fields -e dns.qry.name
    ```

    Compare these results with the `data-exfil.tk` queries from Step 5. The long names and the suspicious domain should overlap significantly. Normal DNS queries rarely exceed 30-40 characters. Queries over 50 characters with non-human-readable content are a reliable indicator of DNS tunneling or data exfiltration.

---

**Record Your Findings**

- What is the source IP generating these queries? (`10.0.2.45`)
- How many queries target `data-exfil.tk`?
- What is the average length of the query names for this domain?
- Pick two or three sample subdomains and record them. Do they look like human-readable hostnames or encoded data?
- Do the subdomains contain only hexadecimal characters (0-9, a-f)?

---

### Step 7: Extract the Subdomain Portions

At this point, you have confirmed three indicators of DNS tunneling: high query volume to a single domain, long subdomain names, and a suspicious TLD. The next step is to extract and decode the data.

Each query follows the pattern `[hex-data].data-exfil.tk`. To isolate just the hex-encoded subdomains, use `cut` to extract the field before the first dot.

!!! target "Extract the hex subdomains"
    Run this on the analysis container. The `cut -d. -f1` stage isolates the subdomain (the hex data) before the first dot of each query name.

    ```bash
    tshark -r dns-tunnel.pcap -Y "dns.qry.name contains data-exfil.tk and dns.flags.response == 0" -T fields -e dns.qry.name | cut -d. -f1
    ```

    The output is a list of hex strings; one per query. Each string is a chunk of the exfiltrated data. In order, they form a continuous stream of hex-encoded content. At this point you can already see the pattern: the attacker split the stolen data into fixed-size hex chunks and sent each chunk as a subdomain in a separate DNS query.

### Step 8: Decode the Exfiltrated Data

You now have all the pieces. The subdomains are hex-encoded data, sent in order across multiple queries. To reconstruct the original data, you need to concatenate all the hex chunks and convert them from hex to ASCII.

!!! target "Decode the exfiltrated data"
    Run this on the analysis container. The full pipeline combines every hex chunk and converts it back to ASCII, revealing the stolen data in plain text.

    ```bash
    tshark -r dns-tunnel.pcap -Y "dns.qry.name contains data-exfil.tk and dns.flags.response == 0" -T fields -e dns.qry.name | cut -d. -f1 | tr -d '\n' | xxd -r -p
    ```

    The output is the decoded stolen data in plain text. If the output appears garbled, verify that the filter is correct and that you are only extracting query names (not responses).

Here is what each stage of the pipeline does:

- `tshark ...` extracts the full query name from each matching DNS request
- `cut -d. -f1` isolates the subdomain; the hex data before the first dot
- `tr -d '\n'` removes newlines, concatenating all hex chunks into one continuous string
- `xxd -r -p` converts the hex string back into ASCII text (`-r` for reverse/hex-to-binary, `-p` for plain hex input without address columns)

The four-stage pipeline is the core technique for this exercise. Each tool handles one transformation, and piping them together produces the final decoded output.

### Step 9: Read the Decoded Output

The decoded output reveals patient records containing names, Social Security numbers, dates of birth, and medical diagnoses. These are Protected Health Information (PHI) from MediCare's billing system. The records include fields such as patient name, SSN, date of birth, diagnosis code, and treating physician.

The decoded text is the data that was exfiltrated from the billing workstation. The attacker's tool read the patient database, hex-encoded the contents, and sent each chunk out as a DNS query to `data-exfil.tk`. On the other end, the attacker's DNS server collected the queries and reassembled the data.

Embedded within the decoded data is the flag:

```
FLAG:OCR{<flag_here>}
```

Record the flag and submit it to complete the exercise.

Take a moment to consider the full attack chain: malware on the billing workstation read the patient database, encoded it as hex, split it into chunks that fit within DNS label length limits, and sent each chunk as a subdomain query to an attacker-controlled domain. The attacker's DNS server logged every query and reassembled the data. At no point did the attacker need to establish a direct connection to an external server; the data flowed through normal DNS infrastructure.

## Analysis Questions

**1. Why is DNS tunneling particularly difficult to detect compared to other exfiltration methods?**

??? note "Reveal Answer"

    DNS traffic is expected on every network and is almost never blocked. The queries are technically valid DNS requests; they resolve to real IPs. Firewalls, proxies, and most security tools ignore DNS traffic entirely. The encoded data in the subdomain is invisible to tools that do not inspect query content. Unlike HTTP or HTTPS exfiltration, DNS tunneling does not require the attacker to set up a web server or establish a direct TCP connection. The data flows through the normal DNS resolution infrastructure, making it nearly invisible to network monitoring.

**2. The decoded data contained patient records with SSNs. What makes this a HIPAA breach rather than just a security incident?**

??? note "Reveal Answer"

    Protected Health Information (PHI) was exfiltrated outside the organization. HIPAA defines a breach as the unauthorized acquisition, access, use, or disclosure of PHI that compromises the security or privacy of that information. The decoded data showed 347 patient records with names, SSNs, dates of birth, and diagnoses; all of which qualify as PHI under HIPAA. Because the breach affects more than 500 individuals, the organization must notify the Department of Health and Human Services, affected individuals, and potentially the media within 60 days of discovery.

**3. How would you prevent DNS tunneling on a corporate network?**

??? note "Reveal Answer"

    Deploy DNS security solutions that inspect query content and detect anomalous patterns (Cisco Umbrella, Infoblox, or Palo Alto DNS Security). Set thresholds for query volume per host per domain and alert when they are exceeded. Monitor for unusually long subdomain names; legitimate subdomains rarely exceed 20 characters. Restrict which internal systems can make external DNS queries by routing all DNS through internal resolvers. Use DNS forwarding restrictions to limit which external resolvers your internal servers contact. Block queries to known-suspicious TLDs such as `.tk`, `.ml`, and `.ga`. Implement DNS response policy zones (RPZs) to enforce domain blocklists at the resolver level.

## Key Takeaways

- DNS tunneling hides exfiltrated data inside normal-looking DNS queries.
- The subdomain portion of each query carries a chunk of hex-encoded stolen data.
- The decode pipeline (`tshark` to `cut` to `tr` to `xxd`) converts captured DNS queries back into readable data.
- Detection requires monitoring query volume, subdomain length, and domain reputation.
- DNS-based exfiltration bypasses firewalls because DNS is almost never blocked.
- A single compromised workstation can exfiltrate hundreds of records without triggering traditional security controls.
- In healthcare environments, DNS exfiltration of patient records triggers HIPAA breach notification requirements.
- Combining `tshark` field extraction with standard Unix text processing tools (`cut`, `tr`, `xxd`) is a powerful forensics technique that extends well beyond this specific scenario.
