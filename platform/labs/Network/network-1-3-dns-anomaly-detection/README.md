# DNS Query Anomaly Detection - Walkthrough

## Lab Overview

This lab teaches DNS security analysis by examining DNS query logs to detect malware command-and-control (C2) communication and data exfiltration. You'll learn to differentiate normal DNS traffic from malicious patterns and identify compromised systems.

**Difficulty**: Beginner
**Estimated Time**: 45 minutes
**Focus**: Blue team / Defensive security / Threat detection

## Prerequisites

- Basic understanding of DNS (Domain Name System)
- Familiarity with command-line tools (grep, awk, curl)
- Understanding of network protocols
- Knowledge of what malware C2 communication is

## Learning Objectives

By completing this lab, you will:
1. Understand DNS fundamentals and why attackers abuse DNS
2. Recognize malicious DNS patterns in query logs
3. Identify data exfiltration via DNS tunneling/subdomains
4. Use command-line tools to analyze DNS logs
5. Differentiate legitimate DNS traffic from C2 communication
6. Extract indicators of compromise (IOCs) from DNS data

## Background

### What is DNS?

DNS (Domain Name System) is the internet's phone book - it translates human-readable domain names (like `google.com`) into IP addresses (like `142.250.80.46`) that computers use to communicate.

### Why Attackers Abuse DNS

DNS is an attractive target for attackers because:

1. **Always Allowed**: Firewalls rarely block DNS (would break internet connectivity)
2. **Blends In**: Networks generate thousands of legitimate DNS queries daily
3. **Data Channel**: Can encode stolen data in subdomain names
4. **Hard to Detect**: Automated security tools often miss subtle malicious patterns
5. **Bypasses Security**: Traditional security controls focus on HTTP/HTTPS, not DNS

### Common DNS Attack Techniques

**Command-and-Control (C2) Communication**:
- Malware queries attacker-controlled domains to receive commands
- Uses DNS as a covert communication channel
- Example: `malware.evil.com` resolves to attacker's C2 server

**Data Exfiltration**:
- Stolen data encoded in subdomain names
- Example: `dXNlcjpwYXNzd29yZA.exfil.evil.com` (Base64 encoded data)
- Each query can leak small amounts of data
- Hundreds of queries can exfiltrate entire files

**Domain Generation Algorithms (DGA)**:
- Malware generates random domain names algorithmically
- Makes blocking difficult (new domains every day)
- Example: `a7f9d2e4c1b8.malware.tk`

### Why This Matters for Defenders

- DNS analysis is a critical SOC analyst skill
- Many breaches involve DNS-based C2 communication
- Early detection of malicious DNS can prevent data theft
- DNS logs provide evidence for incident response
- Understanding attacker techniques improves defensive posture

## Step-by-Step Solution

### Step 1: Access the DNS Query Logs

The DNS query logs are available via HTTP on the target server:

```bash
# View logs directly in browser
http://10.100.{user_id}.10/dns.log

# Or download for local analysis
curl http://10.100.{user_id}.10/dns.log -o dns.log
```

### Step 2: Understand the Log Format

Each DNS query log entry follows this format:
```
TIMESTAMP SOURCE_IP QUERY_TYPE DOMAIN -> IP_ADDRESS
```

**Example**:
```
2024-01-04 14:23:15 10.50.1.45 A google.com -> 142.250.80.46
```

**Fields**:
- **Timestamp**: When the DNS query was made
- **Source IP**: Which workstation/device made the query
- **Query Type**: A (IPv4), AAAA (IPv6), TXT, etc.
- **Domain**: The domain name being looked up
- **IP Address**: The resolved IP address

### Step 3: Identify Most Queried Domains

Normal users query a variety of domains. Malware repeatedly queries the same C2 domain.

**Command to count queries per domain**:
```bash
cat dns.log | grep -v '^#' | awk '{print $4}' | sort | uniq -c | sort -rn | head -20
```

**Expected output**:
```
     45 c2-dns-3xf1ltr4t10n.tk      <- SUSPICIOUS! Way more than normal
     12 google.com
      8 microsoft.com
      7 office365.com
      6 azure.com
      5 amazonaws.com
      ...
```

**What to notice**:
- One domain has significantly more queries (40-50+)
- The domain name looks suspicious: `c2-dns-3xf1ltr4t10n.tk`
- Unusual TLD (`.tk` is commonly used by attackers)
- Pattern suggests the flag: `dns_3xf1ltr4t10n`

### Step 4: Analyze the Suspicious Domain

Let's examine all queries to the suspicious domain:

```bash
grep "c2-dns-3xf1ltr4t10n.tk" dns.log
```

**What you'll see**:
```
2024-01-04 14:25:15 10.50.4.67 A 7f9a2e1c4b8d.c2-dns-3xf1ltr4t10n.tk -> 185.220.101.47
2024-01-04 14:25:23 10.50.4.67 A 9d3f8a6c2e1b.c2-dns-3xf1ltr4t10n.tk -> 185.220.101.47
2024-01-04 14:25:31 10.50.4.67 A a4e7f2d9c8b1.c2-dns-3xf1ltr4t10n.tk -> 185.220.101.47
...
```

**Red flags**:
- **Long random subdomains**: `7f9a2e1c4b8d`, `9d3f8a6c2e1b` (data exfiltration pattern)
- **Same source IP**: All queries from `10.50.4.67` (infected workstation)
- **Same destination IP**: All resolve to `185.220.101.47` (C2 server)
- **High frequency**: Dozens of queries in short time period
- **Unusual TLD**: `.tk` is free and commonly used by attackers

This is classic malware C2 communication with data exfiltration!

### Step 5: Identify the Infected Workstation

```bash
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | awk '{print $2}' | sort -u
```

**Output**:
```
10.50.4.67
```

This is the Radiology department workstation - it's been compromised by malware.

### Step 6: Count Malicious Queries

```bash
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | wc -l
```

**Output**: ~45 queries

This is highly abnormal for a single domain. Normal domains might get 5-10 queries, but 45+ indicates automated malware activity.

### Step 7: Examine the Subdomain Pattern

```bash
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | awk '{print $4}' | head -10
```

**Output**:
```
7f9a2e1c4b8d.c2-dns-3xf1ltr4t10n.tk
9d3f8a6c2e1b.c2-dns-3xf1ltr4t10n.tk
a4e7f2d9c8b1.c2-dns-3xf1ltr4t10n.tk
...
```

**Analysis**:
- Each query has a different random subdomain
- Subdomain length: 12-24 characters
- Pattern: Random hexadecimal-looking strings
- **This is data exfiltration!** Each subdomain encodes stolen data

### Step 8: Find the Flag

The flag is embedded in the DNS logs. Search for it:

```bash
grep "OCR{" dns.log
```

**OR look for analysis comments**:
```bash
grep -i "flag\|alert\|analysis" dns.log
```

**Expected finding**:
```
# 2024-01-04 14:36:45 ANALYSIS: Malware C2 detected - Source: 10.50.4.67, Domain: c2-dns-3xf1ltr4t10n.tk, Pattern: Data exfiltration via DNS
# 2024-01-04 14:36:45 ALERT: Malicious domain pattern contains flag: OCR{dns_3xf1ltr4t10n}
```

**Flag**: `OCR{dns_3xf1ltr4t10n}`

## Key Takeaways

### Normal DNS Traffic Characteristics

**Legitimate queries**:
- Variety of different domains (google.com, microsoft.com, etc.)
- Low frequency per domain (5-10 queries)
- Recognizable business-relevant domains
- Common TLDs (.com, .org, .gov, .net)
- Spread out over time (not rapid-fire)

### Malicious DNS Traffic Characteristics

**Suspicious patterns**:
- High query volume to single domain (40-100+ queries)
- Long random subdomains (data exfiltration)
- Unusual TLDs (.tk, .xyz, .top, .cc, .info)
- Unfamiliar domains (not business-related)
- Rapid succession of queries (automated)
- Same source IP repeatedly querying same base domain
- Suspicious IP addresses (foreign, known bad ranges)

### Data Exfiltration Indicators

**What to look for**:
1. **Changing subdomains**: Each query has different subdomain
2. **Encoded data**: Base64, hex, or random strings in subdomains
3. **Length variation**: Subdomains of varying lengths (10-60+ characters)
4. **High frequency**: Automated queries every few seconds
5. **No caching**: Normal DNS responses are cached; exfiltration isn't

### Command-Line Analysis Skills Learned

**Useful commands**:
- `grep -v '^#'` - Exclude comment lines
- `awk '{print $4}'` - Extract domain column
- `sort | uniq -c` - Count unique occurrences
- `sort -rn` - Sort numerically, reverse (highest first)
- `wc -l` - Count total lines/queries
- `grep -E "pattern"` - Use extended regex for pattern matching

## Defensive Best Practices

### Detection Strategies

1. **Monitor DNS query volume**: Alert on excessive queries to single domain
2. **Analyze TLDs**: Flag uncommon TLDs (.tk, .xyz, .top, .cc)
3. **Detect DGA patterns**: Long random domain names
4. **Baseline normal traffic**: Know what's normal for your network
5. **Use DNS security tools**: Cisco Umbrella, Infoblox, etc.
6. **Correlate with other logs**: Match DNS with firewall, proxy, EDR logs

### Prevention Measures

1. **DNS filtering**: Block known malicious domains and suspicious TLDs
2. **DNS sinkholing**: Redirect malicious queries to controlled servers
3. **Rate limiting**: Limit DNS queries per host
4. **DNS-over-HTTPS (DoH) blocking**: Prevent encrypted DNS bypass
5. **Endpoint protection**: Deploy EDR to detect malware before it communicates
6. **Network segmentation**: Limit which systems can make external DNS queries

### Incident Response Workflow

When you detect malicious DNS activity:

1. **Identify**: Extract C2 domain, infected IP, query count
2. **Isolate**: Quarantine infected workstation immediately
3. **Block**: Add C2 domain to DNS blacklist
4. **Investigate**:
   - Check infected system for malware (EDR scan)
   - Review historical logs for initial infection
   - Identify what data was accessed
5. **Remediate**:
   - Clean/reimage infected system
   - Reset credentials used on that system
   - Patch vulnerabilities that allowed infection
6. **Document**: Create incident report with IOCs
7. **Report**: Notify CISO, potentially law enforcement

## Advanced Analysis

### Scripted DNS Analysis

Create a simple malicious DNS detector:

```bash
#!/bin/bash
# detect_malicious_dns.sh - DNS anomaly detector

LOG_FILE="dns.log"
QUERY_THRESHOLD=30  # Alert if domain queried more than 30 times

echo "Analyzing DNS logs for suspicious patterns..."

# Find high-frequency domains
echo -e "\n[*] High-frequency domain queries:"
grep -v '^#' "$LOG_FILE" | \
    awk '{print $4}' | \
    sort | uniq -c | \
    sort -rn | \
    while read count domain; do
        if [ "$count" -gt "$QUERY_THRESHOLD" ]; then
            echo "[ALERT] $domain queried $count times (threshold: $QUERY_THRESHOLD)"

            # Show source IPs
            echo "  Source IPs:"
            grep "$domain" "$LOG_FILE" | grep -v '^#' | awk '{print $2}' | sort -u | sed 's/^/    /'

            # Check for subdomain pattern
            echo "  Sample queries:"
            grep "$domain" "$LOG_FILE" | grep -v '^#' | awk '{print $4}' | head -3 | sed 's/^/    /'
            echo ""
        fi
    done

# Check for unusual TLDs
echo -e "\n[*] Queries to unusual TLDs:"
grep -v '^#' "$LOG_FILE" | \
    awk '{print $4}' | \
    grep -E '\.(tk|xyz|top|cc|info|pw|gq|ml|ga|cf)$' | \
    sort -u | \
    while read domain; do
        count=$(grep "$domain" "$LOG_FILE" | grep -v '^#' | wc -l)
        echo "[WARNING] $domain (TLD commonly used by attackers, $count queries)"
    done

# Look for long subdomain patterns (data exfiltration)
echo -e "\n[*] Long random subdomains (potential data exfiltration):"
grep -v '^#' "$LOG_FILE" | \
    awk '{print $4}' | \
    grep -E '^[a-z0-9]{15,}\.' | \
    head -5 | \
    sed 's/^/[SUSPICIOUS] /'
```

**Run it**:
```bash
chmod +x detect_malicious_dns.sh
./detect_malicious_dns.sh
```

### Timeline Analysis

Create a timeline of the malware C2 activity:

```bash
# Show when C2 activity started and ended
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | awk '{print $1, $2}' | head -1
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | awk '{print $1, $2}' | tail -1

# Calculate duration
echo "C2 activity duration: approximately X minutes"

# Query frequency (queries per minute)
total_queries=$(grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | wc -l)
echo "Average: ~3-5 queries per minute (automated beacon)"
```

### IOC Extraction

Document Indicators of Compromise (IOCs) for threat intelligence:

```bash
# Extract all IOCs from the incident
echo "=== Indicators of Compromise ==="
echo ""
echo "Malicious Domain:"
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | awk '{print $4}' | cut -d'.' -f2- | sort -u

echo ""
echo "C2 Server IP:"
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | awk '{print $6}' | sort -u

echo ""
echo "Infected Host:"
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | awk '{print $2}' | sort -u

echo ""
echo "Sample Subdomain Patterns:"
grep "c2-dns-3xf1ltr4t10n.tk" dns.log | grep -v '^#' | awk '{print $4}' | head -5
```

**Use these IOCs to**:
- Block the C2 domain in DNS firewall
- Add C2 IP to network blacklist
- Search other logs for the same IOCs
- Share with security community (MISP, ISACs)

## Common Mistakes

### Mistake 1: Not Filtering Comment Lines

**Wrong**:
```bash
cat dns.log | awk '{print $4}'  # Includes comments, breaks analysis
```

**Right**:
```bash
cat dns.log | grep -v '^#' | awk '{print $4}'  # Excludes comments
```

### Mistake 2: Ignoring Subdomains

**Wrong**: Only looking at base domain frequency.

**Right**: Analyze subdomain patterns - data exfiltration uses changing subdomains!

```bash
# See the full subdomain patterns
grep "suspicious-domain.tk" dns.log | awk '{print $4}'
```

### Mistake 3: Missing Context in Logs

**Wrong**: Just finding the domain and stopping.

**Right**: Understand the full context:
- Which workstation is infected?
- When did it start?
- How much data was exfiltrated?
- What's the C2 server IP?

### Mistake 4: Not Checking Unusual TLDs

Many attackers use free TLDs: `.tk`, `.xyz`, `.top`, `.cc`, `.info`

```bash
# Search for unusual TLDs
grep -E '\.(tk|xyz|top|cc|info)$' dns.log
```

## Real-World Application

### Case Study: Real Malware Using DNS

**APT Examples**:
- **DNSMessenger**: Used DNS TXT records for C2 communication
- **FrameworkPOS**: Exfiltrated credit card data via DNS queries
- **Backdoor.Mori**: Used DGA to generate C2 domains

**Recent Campaigns**:
- Many ransomware families use DNS for initial C2 check-in
- Banking trojans exfiltrate credentials via DNS
- APT groups use DNS tunneling for long-term persistence

### SIEM Detection Rules

**Splunk query example**:
```spl
index=dns
| stats count by query
| where count > 30
| eval suspicious_tld=if(match(query, "\.(tk|xyz|top|cc)$"), "Yes", "No")
| where suspicious_tld="Yes"
```

**Sigma rule example**:
```yaml
title: High Frequency DNS Queries to Suspicious TLD
description: Detects potential DNS C2 or exfiltration
detection:
  selection:
    query|endswith:
      - '.tk'
      - '.xyz'
      - '.top'
  timeframe: 10m
  condition: selection | count() > 30
```

### Integration with Security Stack

**How DNS analysis fits in your security program**:

1. **DNS Firewall** (Cisco Umbrella, Infoblox): Block known bad domains
2. **SIEM** (Splunk, ELK): Correlate DNS with other security events
3. **EDR** (CrowdStrike, SentinelOne): Identify malware making DNS queries
4. **Threat Intelligence**: Feed IOCs to security tools
5. **Network Monitor** (Zeek, Suricata): Deep packet inspection of DNS
6. **Sandbox**: Analyze malware samples to extract DNS IOCs

## Conclusion

You've successfully:
- ✅ Analyzed DNS query logs for suspicious patterns
- ✅ Identified malware C2 communication
- ✅ Detected data exfiltration via DNS
- ✅ Distinguished normal DNS traffic from malicious activity
- ✅ Extracted indicators of compromise (IOCs)
- ✅ Applied command-line analysis techniques

**Core skill acquired**: DNS-based threat detection - a critical capability for modern SOC analysts.

### Next Steps

To continue building your skills:

1. **Practice**: Analyze DNS logs from your home network
2. **Learn tools**: Wireshark (packet analysis), Zeek (DNS logging)
3. **Study malware**: Understand how different malware families use DNS
4. **Automate**: Write scripts to detect DNS anomalies
5. **Stay current**: Follow DNS security research and new attack techniques

### Further Learning

**Recommended reading**:
- SANS Reading Room: DNS Tunneling and Exfiltration
- Palo Alto Networks: DNS-based Threats
- Cisco Umbrella: DNS Security Best Practices

**Tools to explore**:
- **Passive DNS**: Track historical DNS resolutions
- **dns2tcp**: DNS tunneling tool (research purposes)
- **iodine**: DNS tunneling implementation
- **DNSChef**: DNS proxy for testing
- **Wireshark**: Packet analysis including DNS

**Certifications**:
- GIAC GCIA (Intrusion Analyst) - Covers DNS analysis
- GIAC GMON (Monitoring) - Network security monitoring
- Blue Team Level 1 (BTL1) - Practical defensive skills

## References

- [RFC 1035 - Domain Names Implementation](https://www.rfc-editor.org/rfc/rfc1035)
- [SANS: Detecting DNS Tunneling](https://www.sans.org/white-papers/)
- [Cisco: DNS Security](https://umbrella.cisco.com/blog/dns-security)
- [MITRE ATT&CK: T1071.004 - Application Layer Protocol: DNS](https://attack.mitre.org/techniques/T1071/004/)
- [Palo Alto Networks: DNS Tunneling Detection](https://www.paloaltonetworks.com/cyberpedia/dns-tunneling)
