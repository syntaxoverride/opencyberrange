# Network Lab 2-4: DNS Data Exfiltration Analysis

## Lab Overview

**Difficulty:** Intermediate
**Estimated Time:** 60 minutes
**Category:** Network Security, DNS Analysis, Data Exfiltration

### Scenario

Marcus Thompson, MediCare Health Systems' Security Analyst, is investigating a concerning alert from the network monitoring system. The IDS flagged an unusual spike in DNS query volume from a single workstation in the billing department. The queries are all valid DNS requests, so they passed through the firewall without issue, but the sheer volume is suspicious.

Marcus suspects **DNS tunneling** - a technique where attackers encode data into DNS queries to exfiltrate information while evading detection. The workstation in question has access to the patient database, making this a potential HIPAA breach if patient data was stolen.

Your task is to analyze the DNS traffic capture and determine if data exfiltration occurred. If so, identify what was stolen and recover the evidence of the attack.

### Learning Objectives

- Understand DNS tunneling and how it's used for data exfiltration
- Identify suspicious DNS query patterns in network traffic
- Use tshark to analyze DNS traffic and detect anomalies
- Extract and decode data hidden in DNS queries
- Recognize the importance of DNS monitoring in security operations

## Walkthrough

### Step 1: Connect to the Lab Environment

Connect to the lab container via SSH:

```bash
ssh analyst@<target_ip>
```

**Credentials:**
- Username: `analyst`
- Password: `MediCare2024#`

### Step 2: Examine the Available Files

List the files in the captures directory:

```bash
ls -lh ~/captures/
```

You should see:
- `dns-tunnel.pcap` - Network capture from the billing workstation

### Step 3: Open the PCAP and Get a Protocol Overview

Use `tshark` to read the PCAP and generate a protocol hierarchy summary. This gives you a high-level view of all protocols present in the capture and their relative traffic volume:

```bash
tshark -r captures/dns-tunnel.pcap -q -z io,phs
```

You should see DNS traffic making up a significant portion of the capture. A disproportionately large amount of DNS traffic from a single workstation is the first red flag.

> **Note:** If a GUI is available, Wireshark can also open this PCAP for visual analysis.

### Step 4: Initial DNS Traffic Analysis

Next, filter to see only DNS queries (not responses) and display the frame number, source IP, and queried domain name:

```bash
tshark -r captures/dns-tunnel.pcap -Y "dns.flags.response == 0" \
  -T fields -e frame.number -e ip.src -e dns.qry.name
```

This shows all DNS queries being made. Scroll through and observe the traffic patterns. Notice how many queries originate from the same source IP.

### Step 5: Identify Suspicious Patterns

DNS tunneling has several telltale signs:

1. **High frequency queries** to the same domain
2. **Long, random-looking subdomains** (20+ characters)
3. **Sequential pattern** - queries happening rapidly in succession
4. **Unusual domain names** - not common services like google.com

**Using tshark to Find Top Queried Domains:**

Extract the base domain (last two labels) from every DNS query and count how often each appears:

```bash
tshark -r captures/dns-tunnel.pcap -Y "dns.flags.response == 0" \
  -T fields -e dns.qry.name | rev | cut -d. -f1-2 | rev | sort | uniq -c | sort -rn | head -20
```

This will show you query counts by domain. Look for domains with an unusually high number of queries (50+). One domain should stand out immediately: `data-exfil.tk`.

You can also look for unusually long query names, which are a hallmark of DNS tunneling:

```bash
tshark -r captures/dns-tunnel.pcap -Y "dns.qry.name.len > 50" \
  -T fields -e dns.qry.name
```

Long, hex-encoded subdomains are a strong indicator that data is being smuggled out via DNS.

### Step 6: Filter for the Suspicious Domain

Now that you have identified the suspicious domain (`data-exfil.tk`), filter to see only queries to that domain:

```bash
tshark -r captures/dns-tunnel.pcap \
  -Y 'dns.qry.name contains "data-exfil.tk"' \
  -T fields -e frame.number -e ip.src -e dns.qry.name
```

You should see 50+ queries to this domain, all from the same source IP: `10.0.2.45`

### Step 7: Examine the Query Structure

Look closely at the output from the previous step. Each query name follows this structure:

```
[hex-encoded-data].data-exfil.tk
```

For example:
```
5041544945...more_hex...2e646174612d657866696c2e746b
```

The subdomain portion (before `.data-exfil.tk`) contains hex-encoded data. Each DNS query carries a chunk of the exfiltrated data encoded as a hex string in the subdomain.

### Step 8: Extract the Subdomains

You can extract all the subdomains using `tshark`:

```bash
cd ~/captures/
tshark -r dns-tunnel.pcap -Y "dns.qry.name contains data-exfil.tk and dns.flags.response == 0" \
  -T fields -e dns.qry.name
```

This will list all the full domain names. The part before `.data-exfil.tk` is the hex-encoded data.

### Step 9: Extract and Decode the Data

To extract just the subdomain portions (the hex data):

```bash
tshark -r dns-tunnel.pcap -Y "dns.qry.name contains data-exfil.tk and dns.flags.response == 0" \
  -T fields -e dns.qry.name | cut -d. -f1
```

Now, to concatenate all the hex chunks and decode them:

```bash
tshark -r dns-tunnel.pcap -Y "dns.qry.name contains data-exfil.tk and dns.flags.response == 0" \
  -T fields -e dns.qry.name | cut -d. -f1 | tr -d '\n' | xxd -r -p
```

**Command Breakdown:**
- `tshark -r dns-tunnel.pcap` - Read the PCAP file
- `-Y "dns.qry.name contains data-exfil.tk and dns.flags.response == 0"` - Filter for queries to suspicious domain
- `-T fields -e dns.qry.name` - Extract only the query name field
- `cut -d. -f1` - Split by dots and take first field (the subdomain)
- `tr -d '\n'` - Remove newlines to concatenate all hex strings
- `xxd -r -p` - Decode from hex to ASCII

### Step 10: Analyze the Exfiltrated Data

The decoded output will show:

```
PATIENT_DATABASE_EXPORT|Records:347|Date:2024-12-15|
Patient:John_Doe,SSN:123-45-6789,DOB:1975-03-21,Diagnosis:Hypertension|
Patient:Jane_Smith,SSN:987-65-4321,DOB:1982-07-14,Diagnosis:Diabetes_Type2|
Patient:Robert_Johnson,SSN:456-78-9123,DOB:1968-11-30,Diagnosis:COPD|
FLAG:OCR{dns_tunn3l_d3t3ct3d}|
Patient:Mary_Williams,SSN:321-54-9876,DOB:1990-05-18,Diagnosis:Asthma|
EXFIL_COMPLETE:TRUE
```

**The flag is: `OCR{dns_tunn3l_d3t3ct3d}`**

### Step 11: Document Your Findings

As a security analyst, you should document:

1. **Infected System:** IP 10.0.2.45 (billing workstation)
2. **Attack Vector:** DNS tunneling via domain data-exfil.tk
3. **C2 Server:** Resolved to 185.220.101.47
4. **Data Stolen:** Patient database records (347 records)
5. **Sensitive Data:** Patient names, SSNs, DOBs, diagnoses
6. **HIPAA Breach:** Yes - PHI (Protected Health Information) exfiltrated
7. **Duration:** Approximately 3-5 minutes of rapid DNS queries
8. **Evidence:** PCAP file with 50+ suspicious queries

## Key Indicators of DNS Tunneling

1. **High Query Volume:** 50+ queries to same domain in short time
2. **Long Subdomains:** 20-30+ character random hex strings
3. **Unusual Domain:** data-exfil.tk (not a legitimate service)
4. **Rapid Succession:** Queries every 1-3 seconds (normal DNS is sporadic)
5. **Consistent Source:** All queries from single infected host
6. **Encoding Pattern:** Hex-encoded data chunks

## Detection Methods

### Command-Line Analysis
```bash
# Protocol hierarchy overview
tshark -r dns-tunnel.pcap -q -z io,phs

# Count queries per base domain
tshark -r dns-tunnel.pcap -Y "dns.flags.response == 0" -T fields -e dns.qry.name | \
  rev | cut -d. -f1-2 | rev | sort | uniq -c | sort -rn

# Find long query names (indicator of tunneling)
tshark -r dns-tunnel.pcap -Y "dns.qry.name.len > 50" -T fields -e dns.qry.name

# Extract all unique domains queried
tshark -r dns-tunnel.pcap -Y "dns.flags.response == 0" -T fields -e dns.qry.name | \
  rev | cut -d. -f1-2 | rev | sort -u
```

## Prevention and Mitigation

1. **DNS Monitoring:**
   - Monitor query volume per host
   - Alert on unusual query lengths
   - Track queries to newly registered domains

2. **DNS Security Solutions:**
   - Implement DNS filtering/inspection
   - Use DNS firewalls
   - Deploy threat intelligence feeds

3. **Network Segmentation:**
   - Limit which systems can make external DNS queries
   - Use internal DNS with forwarding restrictions

4. **Endpoint Protection:**
   - Deploy EDR solutions that detect DNS tunneling
   - Monitor process network activity
   - Implement application whitelisting

5. **Baseline Monitoring:**
   - Establish normal DNS query patterns
   - Alert on deviations (query count, domain entropy, etc.)

## Additional Challenges

If you want to practice further:

1. **Calculate the data exfiltration rate:**
   - How many bytes per second were exfiltrated?
   - How long would it take to exfiltrate a 100MB database?

2. **Identify the timeline:**
   - When did the tunneling start?
   - How long did the exfiltration last?
   - Was there any normal traffic before/after?

3. **Build a detection rule:**
   - Write a Snort/Suricata rule to detect this pattern
   - Create a Python script to analyze PCAP for DNS tunneling

4. **Alternative decoding:**
   - Use Python with scapy to extract and decode the data
   - Write a custom parser for the DNS queries

## Resources

- [DNS Tunneling Explained](https://www.paloaltonetworks.com/cyberpedia/what-is-dns-tunneling)
- [Detecting DNS Tunneling](https://www.sans.org/reading-room/whitepapers/dns/detecting-dns-tunneling-34152)
- [tshark Command Examples](https://tshark.dev/)

## Conclusion

DNS tunneling is a stealthy exfiltration technique that abuses a trusted protocol to bypass security controls. By understanding the patterns and using proper analysis tools, security analysts can detect and prevent these attacks. Always monitor DNS traffic for unusual patterns, especially high-frequency queries to suspicious domains with long, encoded subdomains.

---

**Flag:** `OCR{dns_tunn3l_d3t3ct3d}`
