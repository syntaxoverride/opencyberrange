# Exercise 1.1: Port Scan Detection

## Before You Begin

Exercise 1.1 is the first exercise in the Network Log Analysis track. Before you start, confirm the following:

- Your VPN connection to the lab environment is active.
- You have a terminal open and ready for command input.
- You can reach exercise targets by pinging the gateway or running a quick connectivity check.

If your VPN is not connected, return to the Getting Started chapter and complete the connection steps before continuing.

## Scenario

MediCare Regional Hospital's firewall has been generating alerts about an unusual volume of denied connections over the past 24 hours. The security operations center has flagged the activity for investigation. As a security analyst on the team, you need to pull the firewall logs, analyze the connection data, and determine whether a port scan is in progress. If it is, you must identify the source IP responsible.

## Your Objectives

- Download and examine firewall logs from the target machine.
- Identify which source IP is generating abnormal traffic.
- Determine whether the traffic pattern matches a port scan.
- Find and submit the flag.

## Background: What Is a Port Scan?

Before an attacker can exploit a service, they need to know what services are running. A port scan is a reconnaissance technique in which an attacker sends connection attempts to many ports on a target system, observing which ports respond and which are filtered or closed.

Normal users connect to a small number of specific services; a web browser hits port 80 or 443, an SSH session connects to port 22. A scanner, by contrast, hits dozens or hundreds of ports in rapid succession, looking for anything that answers.

Defenders detect port scans by watching for a single source IP making many connection attempts to different destination ports within a short time window. Firewall logs are one of the best places to spot this behavior, because they record every connection attempt regardless of whether it succeeds.

## Tool Primer: The Unix Log Analysis Pipeline

Exercise 1.1 is your first log analysis lab, so take a moment to understand the core tools you will use throughout this track. Log analysis on the command line follows a pipeline pattern: you download the data, filter it, extract the fields you care about, then count and rank results.

**`curl`** downloads files from a remote server. You use it to pull log files from the target machine.

```bash
curl http://<target_ip>/firewall.log -o firewall.log
```

**`grep`** filters lines that match a pattern. You can also invert the match with `-v` to exclude lines. Log files often contain comment lines starting with `#`, which you strip out before analysis.

```bash
grep -v '^#' firewall.log        # exclude comment lines
grep "DENY" firewall.log         # show only denied connections
```

**`awk '{print $N}'`** extracts a specific column from whitespace-delimited output. Column numbering starts at 1.

```bash
awk '{print $3}'                 # extract the third column
```

**`cut -d':' -f1`** splits a field on a delimiter and selects a sub-field. Splitting on a colon is useful when a column like `203.0.113.66:45123` contains both an IP and a port joined by a colon.

```bash
cut -d':' -f1                    # extract everything before the colon
cut -d':' -f2                    # extract everything after the colon
```

**`sort | uniq -c | sort -rn`** is the counting pipeline. It sorts input so identical lines are adjacent, counts consecutive duplicates, then sorts the counts in descending numerical order. The pipeline tells you which values appear most often.

**`wc -l`** counts lines, which is useful for getting totals after filtering.

The full pipeline concept is: **download -> filter -> extract -> count -> rank**.

## Walkthrough

### Step 1: Launch the Exercise

In the Open Cyber Range interface, navigate to **Network -> Level 1 -> Port Scan Detection** and start the lab. Wait until the status indicator shows **Running**, then note the target IP displayed on the lab page. You will substitute this value wherever you see `<target_ip>` in the commands below.

### Step 2: Download the Firewall Log

!!! kali "Download the firewall log from the target"
    Pull the log file from the target machine to your local working directory. The `curl` command runs from your analyst Kali workstation and saves the log locally for offline analysis.

    ```bash
    curl http://<target_ip>/firewall.log -o firewall.log
    ```

    You should see a progress bar followed by a confirmation that the file has been saved. If the download fails, verify your VPN connection and confirm the target IP is correct.

### Step 3: Examine the Log Format

!!! kali "Preview the log structure"
    Look at the first few non-comment lines to understand the structure of the data. The `grep -v '^#'` strips comment lines so you see only real log records.

    ```bash
    grep -v '^#' firewall.log | head -10
    ```

Each line follows this format:

```
TIMESTAMP ACTION SOURCE_IP:PORT -> DEST_IP:PORT [SERVICE]
```

For example:

```
2024-01-03 22:15:30 DENY 203.0.113.66:45123 -> 10.10.3.50:22 [SSH]
```

The fields break down as follows:

| Position | Field | Example |
|----------|-------|---------|
| $1 $2 | Date and time | `2024-01-03 22:15:30` |
| $3 | Action (ALLOW or DENY) | `DENY` |
| $4 | Source IP and port | `203.0.113.66:45123` |
| $5 | Arrow | `->` |
| $6 | Destination IP and port | `10.10.3.50:22` |
| $7 | Service label | `[SSH]` |

Note that because the timestamp occupies two columns (date and time), the action is in column 3, the source address is in column 4, and the destination address is in column 6.

### Step 4: Count Connection Attempts per Source IP

!!! kali "Count connection attempts per source IP"
    Now build the analysis pipeline. You want to know how many connection attempts each source IP made. Strip comments, extract the source address column, split off the port number, then count and rank.

    ```bash
    grep -v '^#' firewall.log | awk '{print $4}' | cut -d':' -f1 | sort | uniq -c | sort -rn
    ```

    The output shows each source IP alongside its total number of connection attempts, sorted from most to least.

---

**Record Your Findings**

Write down the top five source IPs and their connection counts from the output above. One IP should have a significantly higher count than all others.

| Source IP | Connection Attempts |
|-----------|-------------------|
| | |
| | |
| | |
| | |
| | |

---

### Step 5: Analyze the Suspicious IP

You should see one IP with approximately 80 connection attempts, while normal IPs in the log show only 6 to 12 attempts each. That outlier is your suspected scanner.

!!! kali "Isolate traffic from the suspicious IP"
    Filter the log to show only entries from the suspicious IP. Replace the IP below with the one you identified in Step 4.

    ```bash
    grep "203.0.113.66" firewall.log
    ```

Examine the output. You are looking for two indicators of a port scan:

- **Many different destination ports.** A normal user connects to one or two services. A scanner tries many.
- **All DENY actions.** The scanner is probing ports that the firewall blocks, so none of the attempts succeed.

Scroll through the results and confirm both of these patterns are present.

### Step 6: Count Unique Ports Scanned

!!! kali "Count unique destination ports targeted"
    Quantify the scan by counting how many distinct destination ports the suspicious IP targeted.

    ```bash
    grep "203.0.113.66" firewall.log | awk '{print $6}' | cut -d':' -f2 | sort -u | wc -l
    ```

    The `grep | awk | cut | sort -u | wc -l` pipeline filters for the suspicious IP, extracts the destination address column, splits off the port number, removes duplicates, and counts the remaining unique values.

---

**Record Your Findings**

- Suspicious source IP: _______________
- Total connection attempts from this IP: _______________
- Number of unique destination ports targeted: _______________
- Action on all attempts (ALLOW or DENY): _______________

Based on these findings, does the traffic pattern match a port scan? _______________

---

### Step 7: Find the Flag

!!! kali "Search the log for the flag"
    The flag is embedded in the log file itself, inside a comment line. Search for the flag prefix.

    ```bash
    grep "OCR{" firewall.log
    ```

    You should see a line beginning with `#` that contains the flag. Copy it and submit it in the lab interface.

The flag is in `OCR{<flag_here>}` format.

## Analysis Questions

Work through these questions to deepen your understanding of the techniques used in this exercise.

**1. How does a port scan differ from normal network traffic in a firewall log?**

??? note "Reveal Answer"

    Normal traffic connects to a small number of specific services with a mix of ALLOW and DENY actions. A port scan shows one IP attempting connections to dozens of different destination ports, almost all DENY, in rapid succession. The volume, variety of ports, and uniform denial are the distinguishing characteristics.

**2. The scanner's IP had approximately 80 connection attempts while normal users had 6 to 12. What threshold would you set for an automated alert?**

??? note "Reveal Answer"

    A reasonable threshold is 20 to 30 unique destination ports from a single source within a 5-minute window. A threshold in that range sits well above normal user behavior but is sensitive enough to catch even slow scans. Production environments tune this value based on baseline traffic patterns and acceptable false-positive rates.

**3. All of the scanner's attempts were DENY. What does this tell you about the firewall configuration?**

??? note "Reveal Answer"

    The firewall is properly configured to block unauthorized access to those ports. However, the scan still provides the attacker with useful information; they now know which ports are filtered versus which might be open on other targets. A well-configured firewall stops the exploitation but does not stop the reconnaissance. Detecting the scan early allows defenders to block the source IP entirely before the attacker moves to the next phase.

## Key Takeaways

- Firewall logs record every connection attempt, both allowed and denied.
- Port scans stand out because one IP probes many ports in a short time.
- The `grep` / `awk` / `sort` / `uniq` pipeline is the fundamental technique for command-line log analysis.
- Comment lines in log files can contain analyst notes and embedded data.
- Detecting a scan early allows defenders to block the attacker before they move from reconnaissance to exploitation.
