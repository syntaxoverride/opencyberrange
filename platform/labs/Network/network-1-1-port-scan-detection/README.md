# Suspicious Port Scan Detection - Walkthrough

## Lab Overview

This lab teaches network defense fundamentals by analyzing firewall logs to detect port scanning activity. You'll learn to differentiate normal network traffic from reconnaissance attempts and extract attacker information from logs.

**Difficulty**: Beginner
**Estimated Time**: 30-45 minutes
**Focus**: Blue team / Defensive security

## Prerequisites

- Basic understanding of TCP/IP and ports
- Familiarity with command-line tools (grep, awk, curl)
- Understanding of what firewalls do

## Learning Objectives

By completing this lab, you will:
1. Understand what port scanning is and why attackers do it
2. Recognize port scan patterns in firewall logs
3. Use command-line tools to analyze log files
4. Differentiate normal traffic from malicious reconnaissance
5. Extract and document attacker information

## Background

**Port Scanning**: The process of probing a system to identify open ports and running services. This is typically the first phase of a cyber attack, where attackers map the network to find potential entry points.

**Why this matters for defenders**:
- Port scans indicate reconnaissance before an attack
- Early detection allows proactive blocking
- Understanding scan patterns helps identify attacker tools and intentions
- Log analysis is a core SOC analyst skill

## Step-by-Step Solution

### Step 1: Access the Firewall Logs

The firewall logs are available via HTTP on the target server:

```bash
# View logs directly in browser
http://10.100.{user_id}.10/firewall.log

# Or download for local analysis
curl http://10.100.{user_id}.10/firewall.log -o firewall.log
```

### Step 2: Understand the Log Format

Each log entry follows this format:
```
TIMESTAMP ACTION SOURCE_IP:PORT -> DEST_IP:PORT [SERVICE]
```

**Example**:
```
2024-01-03 22:15:30 DENY 203.0.113.66:45123 -> 10.10.3.50:22 [SSH]
```

**Fields**:
- **Timestamp**: When the connection attempt occurred
- **Action**: ALLOW (permitted) or DENY (blocked)
- **Source**: Attacker/client IP and port
- **Destination**: Your server IP and port
- **Service**: What service is on that port

### Step 3: Find Suspicious Source IPs

Normal users connect to a few specific services. Scanners probe many ports.

**Command to count connection attempts per IP**:
```bash
cat firewall.log | grep -v '^#' | awk '{print $3}' | cut -d':' -f1 | sort | uniq -c | sort -rn
```

**Expected output**:
```
     80 203.0.113.66      <- SUSPICIOUS! Way more than others
     12 10.50.1.15
      8 10.50.2.8
      6 10.50.1.22
      ...
```

The IP with significantly more attempts (60-80+) is likely the scanner.

### Step 4: Analyze the Suspicious IP

Let's examine what `203.0.113.66` (example IP) is doing:

```bash
grep "203.0.113.66" firewall.log
```

**What to look for**:
- Many different destination ports
- Sequential port numbers (20, 21, 22, 23, 24...)
- All DENY actions (attacker has no legitimate access)
- Rapid timestamps (scan completes in minutes)

### Step 5: Count Ports Scanned

```bash
grep "203.0.113.66" firewall.log | awk '{print $5}' | cut -d':' -f2 | sort -u | wc -l
```

If the count is 30+, this is definitely a port scan.

### Step 6: Find the Flag

The flag is embedded in the firewall logs. Look for:
- Comment lines (starting with `#`)
- Analysis or alert messages
- Summaries related to the scanning activity

**Search for flag**:
```bash
grep "Flag:" firewall.log
# Or
grep "OCR{" firewall.log
```

**Expected finding**:
```
# 2024-01-03 22:32:50 ANALYSIS: Port scan detected - Source: 203.0.113.66, Ports: 80, Flag: OCR{p0rt_sc4n_d3t3ct3d}
```

## Key Takeaways

### Port Scan Indicators

**Normal traffic characteristics**:
- Connects to 1-3 specific services
- Spread out over time (hours/days)
- Mix of ALLOW and occasional DENY
- Consistent source IPs (employees, systems)

**Port scan characteristics**:
- Probes 20-100+ different ports
- Rapid succession (minutes)
- Mostly/all DENY (unauthorized probing)
- Unfamiliar external source IP
- Sequential or systematic port pattern

### Defensive Best Practices

1. **Monitor firewall logs** for connection patterns
2. **Set up alerts** for excessive failed connections from single IPs
3. **Implement rate limiting** to slow down scanners
4. **Use IDS/IPS** (Intrusion Detection/Prevention Systems) to automate detection
5. **Block known scanner IPs** at the firewall
6. **Document and report** scanning activity

### Command-Line Analysis Skills

**Useful commands learned**:
- `grep -v '^#'` - Exclude comment lines
- `awk '{print $3}'` - Extract specific column (source IP)
- `cut -d':' -f1` - Split on colon, take first part
- `sort | uniq -c` - Count unique occurrences
- `sort -rn` - Sort numerically, reverse (highest first)
- `wc -l` - Count lines

## Common Mistakes

### Mistake 1: Not Filtering Comments

**Wrong**:
```bash
cat firewall.log | awk '{print $3}'  # Includes comment lines
```

**Right**:
```bash
grep -v '^#' firewall.log | awk '{print $3}'  # Excludes comments
```

### Mistake 2: Counting All Connections

**Wrong**: Looking at total connections without considering uniqueness.

**Right**: Count unique destination ports per source IP to identify scanning.

### Mistake 3: Missing the Flag in Comments

The flag is in a comment line. Make sure to:
```bash
grep "OCR{" firewall.log  # Search entire file, including comments
```

## Real-World Application

### Automated Detection

In production environments, this analysis is automated:

**SIEM Rules** (Security Information and Event Management):
```
IF source_ip has > 20 failed connections to different ports in 5 minutes
THEN generate alert "Possible port scan detected"
AND block source_ip for 1 hour
```

**IDS Signatures** (Intrusion Detection System):
- Snort/Suricata have built-in port scan detection
- Configure thresholds based on your environment
- Generate alerts for security team review

### Incident Response Workflow

When you detect a port scan:

1. **Identify**: Extract attacker IP, time range, ports scanned
2. **Block**: Add source IP to firewall deny list
3. **Document**: Create incident report with evidence
4. **Investigate**: Check if scan was successful (any connections ALLOW?)
5. **Search**: Look for the IP in other logs (web, auth, IDS)
6. **Report**: Notify CISO/management if part of larger attack

### Types of Scans

**TCP SYN Scan** (most common):
- Sends SYN packets to probe ports
- Doesn't complete 3-way handshake
- Appears as failed connections in logs

**TCP Connect Scan**:
- Completes full connection
- Appears as successful then immediate disconnect

**UDP Scan**:
- Harder to detect (connectionless protocol)
- Look for ICMP "port unreachable" responses

**Stealth Scans**:
- Slow scans spread over hours/days
- Randomized source ports and timing
- Harder to detect, requires correlation

## Advanced Analysis

### Scripted Detection

Create a simple scan detector:

```bash
#!/bin/bash
# detect_scans.sh - Simple port scan detector

LOG_FILE="firewall.log"
THRESHOLD=20

echo "Analyzing firewall logs for port scans..."

grep -v '^#' "$LOG_FILE" | \
    awk '{print $3}' | \
    cut -d':' -f1 | \
    sort | uniq -c | \
    sort -rn | \
    while read count ip; do
        if [ "$count" -gt "$THRESHOLD" ]; then
            echo "[ALERT] Possible scan from $ip ($count attempts)"

            # Show which ports were targeted
            echo "  Ports scanned:"
            grep "$ip" "$LOG_FILE" | awk '{print $5}' | cut -d':' -f2 | sort -u | head -10
        fi
    done
```

### Visualization

Convert logs to timeline:
```bash
grep "203.0.113.66" firewall.log | awk '{print $1, $2, $5}' | cut -d':' -f1,2,4
```

This shows time progression and port sequence.

## Conclusion

You've successfully:
- ✅ Analyzed firewall logs for suspicious patterns
- ✅ Identified port scanning activity
- ✅ Distinguished normal traffic from reconnaissance
- ✅ Extracted attacker information using command-line tools
- ✅ Documented the attack pattern

**Core skill acquired**: Log analysis for threat detection - a fundamental SOC analyst capability.

## References

- [NMAP Port Scanning Techniques](https://nmap.org/book/man-port-scanning-techniques.html)
- [SANS Reading Room - Detecting Port Scans](https://www.sans.org/reading-room/whitepapers/detection/)
- [Firewall Log Analysis Best Practices](https://www.cisco.com/c/en/us/support/docs/security/asa-5500-x-series-next-generation-firewalls/200150-Firewall-Log-Analysis.html)
