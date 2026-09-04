# Exercise 1.3: DNS Anomaly Detection

## Before You Begin

In Exercise 1.1 you analyzed firewall logs to trace a port-scanning attack, and in Exercise 1.2 you moved to HTTP packet analysis using Wireshark. this exercise returns to text-based log analysis but shifts the focus to DNS; the Domain Name System. DNS is a protocol that attackers frequently abuse because it is almost never blocked by firewalls. The same command-line skills you practiced in Exercise 1.1 (`grep`, `awk`, `sort`, `uniq`) apply directly here.

## Scenario

MediCare's network monitoring system has flagged an unusual volume of DNS queries originating from a workstation in the Radiology department. DNS traffic is normally invisible to most security tools, making it a favorite channel for malware communication and data theft. Your task is to analyze the DNS query logs captured by MediCare's internal DNS server and determine whether the traffic is malicious.

## Your Objectives

- Download and examine DNS query logs from the target machine.
- Identify which domain is generating an abnormal query volume.
- Analyze the subdomain patterns for signs of data exfiltration.
- Identify the infected workstation.
- Find and submit the flag.

## Background: DNS as an Attack Channel

DNS translates human-readable domain names (like `google.com`) into IP addresses (like `142.250.80.46`) that computers use to communicate. Every time you visit a website, your machine sends a DNS query to a DNS server to resolve the domain name. Resolution happens constantly and in large volumes across any network.

Firewalls almost never block DNS traffic because doing so would break internet connectivity for every user and application on the network. Attackers exploit this blind spot in two primary ways:

**Command-and-Control (C2) via DNS.** Malware installed on a compromised machine queries an attacker-controlled domain at regular intervals. The DNS responses contain encoded commands that tell the malware what to do next; download additional payloads, move laterally, or begin exfiltrating data.

**Data exfiltration via DNS.** Stolen data is encoded and embedded in the subdomain portion of a DNS query. For example, a query for `7f9a2e1c4b8d.evil.com` carries the hex-encoded chunk `7f9a2e1c4b8d` to the attacker's DNS server. Each query carries a small piece, and the attacker's server reassembles the chunks to reconstruct the stolen data.

Red flags that indicate DNS abuse include:

- A high volume of queries to a single domain from one host.
- Long, random-looking subdomain names (often hex or base64 encoded).
- Unusual top-level domains such as `.tk`, `.xyz`, `.top`, or `.cc`.
- All queries from a single source IP, suggesting one infected machine.

## Walkthrough

### Step 1: Launch the Exercise

Start the lab environment and note the target IP address displayed on the launch page. You will use this IP to download the DNS log file.

### Step 2: Download the DNS Log

!!! kali "Download the DNS log from the target"
    Open a terminal on your analyst Kali workstation and download the DNS log from the target machine.

    ```bash
    curl http://<target_ip>/dns.log -o dns.log
    ```

    The `curl -o` flag saves the DNS query log to your current directory.

### Step 3: Examine the Log Format

!!! kali "Preview the DNS log structure"
    View the first several lines of the log to understand its structure.

    ```bash
    head -20 dns.log
    ```

Lines beginning with `#` are comments. Each data line follows this format:

```
TIMESTAMP SOURCE_IP QUERY_TYPE DOMAIN -> IP_ADDRESS
```

For example:

```
2024-01-04 14:23:15 10.50.1.45 A google.com -> 142.250.80.46
```

The fields are:

| Field | Description |
|---|---|
| `TIMESTAMP` | Date and time of the query (date and time occupy two space-separated columns). |
| `SOURCE_IP` | The internal IP address of the machine that made the query. |
| `QUERY_TYPE` | The DNS record type (typically `A` for address lookups). |
| `DOMAIN` | The domain name that was queried. |
| `-> IP_ADDRESS` | The IP address returned by the DNS server. |

### Step 4: Count Queries per Domain

!!! kali "Count queries per domain"
    Use the same pipeline approach from Exercise 1.1 to count how many queries each domain received. Filter out comment lines first, then extract the domain field, sort, count, and display the top 20.

    ```bash
    grep -v '^#' dns.log | awk '{print $4}' | sort | uniq -c | sort -rn | head -20
    ```

    Most domains in the output appear only a handful of times; normal user browsing. One domain stands out with roughly 45 queries, far more than any legitimate site would receive in this timeframe.

---

**Record Your Findings**

List the top five domains by query count from your output:

| Rank | Query Count | Domain |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

Which domain has an unusually high query count? _______________

---

### Step 5: Analyze the Suspicious Domain

!!! kali "Isolate queries to the suspicious domain"
    The domain `c2-dns-3xf1ltr4t10n.tk` has far more queries than any other. Filter the log to show only entries for this domain.

    ```bash
    grep "c2-dns-3xf1ltr4t10n.tk" dns.log
    ```

Examine the output carefully. Notice two things: each query uses a different subdomain, and each subdomain is a string of random hexadecimal characters. A typical entry looks like this:

```
2024-01-04 14:25:42 10.50.4.67 A 7f9a2e1c4b8d.c2-dns-3xf1ltr4t10n.tk -> 185.220.101.47
```

The subdomain `7f9a2e1c4b8d` is not a real hostname; it is a chunk of encoded data being smuggled out of the network through DNS queries. Encoded subdomains like this are the data exfiltration pattern described in the Background section.

### Step 6: Identify the Infected Workstation

!!! kali "Identify the source workstation"
    Determine which internal IP address is generating these queries.

    ```bash
    grep "c2-dns-3xf1ltr4t10n.tk" dns.log | awk '{print $2}' | sort -u
    ```

    The pipeline returns a single source IP: `10.50.4.67`. Every malicious DNS query originates from this one workstation; the infected machine in the Radiology department.

!!! kali "Identify the C2 resolution target"
    Now confirm where these queries are resolving to.

    ```bash
    grep "c2-dns-3xf1ltr4t10n.tk" dns.log | awk '{print $NF}' | sort -u
    ```

    All queries resolve to the same IP address: `185.220.101.47`. That address is the attacker's C2 server, which receives the exfiltrated data encoded in the subdomain names.

---

**Record Your Findings**

Source IP of the infected workstation: _______________

C2 server IP address: _______________

Write down three example subdomains from the malicious queries:

1. _______________
2. _______________
3. _______________

---

### Step 7: Find the Flag

!!! kali "Search the log for the flag"
    Search the log for the flag string.

    ```bash
    grep "OCR{" dns.log
    ```

    Record the flag you find in `OCR{<flag_here>}` format.

## Analysis Questions

**1. The malicious domain uses a `.tk` TLD. Why do attackers favor certain top-level domains?**

??? note "Reveal Answer"

    TLDs like `.tk`, `.xyz`, `.top`, and `.cc` offer free or very cheap domain registration with minimal identity verification. Attackers register disposable domains under these TLDs, use them for a single campaign, and abandon them before they can be traced. Legitimate businesses rarely use these TLDs, which is why their presence in DNS logs is a useful indicator of suspicious activity.

**2. Each DNS query to the malicious domain has a different random subdomain. What is the purpose of this pattern?**

??? note "Reveal Answer"

    Each subdomain contains a chunk of encoded data being exfiltrated from the network. By splitting the stolen data across many DNS queries, the attacker avoids DNS message size limits and makes the traffic appear similar to normal DNS lookups. The C2 server collects all the queries, strips out the subdomain portions, and reassembles the chunks to reconstruct the stolen data.

**3. If you were a network defender, how would you detect this type of DNS abuse automatically?**

??? note "Reveal Answer"

    Set thresholds for DNS query volume per domain per source IP and alert when a single host queries the same domain more than 30 times within a five-minute window. Monitor for unusually long subdomain names; 20 or more characters of random-looking data is a strong indicator of DNS tunneling or exfiltration. Flag queries to domains registered under TLDs known for abuse. Deploy DNS security services that maintain threat intelligence feeds and can block queries to known-malicious domains in real time.

## Key Takeaways

- DNS is almost never blocked by firewalls, making it an attractive covert channel for attackers.
- Malware C2 communication manifests as high-frequency queries from a single host to one unusual domain.
- Data exfiltration via DNS uses changing random subdomains to encode and transmit stolen data in small chunks.
- The same `grep`, `awk`, `sort`, and `uniq` pipeline you used in Exercise 1.1 works equally well on DNS logs.
- Identifying the source IP of malicious DNS queries pinpoints the infected machine on the network.
