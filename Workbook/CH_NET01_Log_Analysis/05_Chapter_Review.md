# Chapter N1: Review

## What You Learned

Over four labs, you built a complete defensive log analysis workflow; starting from a firewall log and a simple `grep` command, progressing through packet capture analysis with `tshark`, DNS anomaly detection, and SSH brute-force identification. Every future chapter in the Network track builds on these analysis skills.

## The Progression You Followed

```mermaid
graph LR
    A["1.1 Firewall Logs"] --> B["1.2 Packet Capture"]
    B --> C["1.3 DNS Logs"]
    C --> D["1.4 Auth Logs"]
    style A fill:#4a90d9,color:#fff
    style D fill:#6aaa64,color:#fff
```

| Exercise | What You Analyzed | What You Detected |
|-----|-------------------|-------------------|
| 1.1 | Firewall logs | Port scan from external IP |
| 1.2 | PCAP (HTTP traffic) | Cleartext credentials in HTTP POST |
| 1.3 | DNS query logs | Malware C2 communication and data exfiltration |
| 1.4 | SSH auth logs | Brute-force login attack |

## Self-Assessment

Answer each question before checking the answer key at the bottom of this page.

1. What Unix command pipeline counts how many times each unique value appears in a column and sorts by frequency?

2. You see 80 DENY entries from one IP in a firewall log. The next highest count is 12. What is happening?

3. What `tshark` display filter shows only HTTP POST requests?

4. A DNS log shows 45 queries to `random-hex.suspicious.tk` from one workstation. What two things does this indicate?

5. In an SSH auth log, what is the difference between "Failed password for admin" and "Failed password for invalid user admin"?

6. You find 60 failed SSH logins from an external IP. What is the first thing you check next?

## Command Cheat Sheet

| Command | What It Does |
|---------|--------------|
| `curl http://<target_ip>/file -o file` | Download a file from the target |
| `grep "pattern" file` | Show lines matching a pattern |
| `grep -v '^#' file` | Exclude comment lines |
| `grep -oE "regex" file` | Extract only the matching portion |
| `awk '{print $N}' file` | Extract column N from each line |
| `cut -d':' -f1` | Split on delimiter, take field 1 |
| `sort \| uniq -c \| sort -rn` | Count unique values, sort by frequency |
| `wc -l` | Count lines |
| `tshark -r file.pcap` | Read and display a PCAP file |
| `tshark -r file.pcap -Y "filter"` | Apply a display filter |
| `tshark -r file.pcap -T fields -e field.name` | Extract specific fields |
| `tshark -r file.pcap -q -z io,phs` | Show protocol hierarchy statistics |
| `tshark -r file.pcap -q -z follow,tcp,ascii,N` | Follow TCP stream N |
| `tshark -r file.pcap -V` | Verbose packet decode |

## Connect the Dots: What Comes Next

Chapter N1 taught you to analyze logs after the fact; reading firewall logs, packet captures, DNS logs, and authentication logs to find evidence of attacks. Chapter N2 (PCAP Forensics) takes you deeper into packet analysis. You will SSH into analyst workstations, work with larger multi-hour captures, and use `tshark` to investigate complex protocol-specific attacks including FTP credential theft, email exfiltration, session hijacking, DNS tunneling data extraction, and a complete multi-stage attack chain.

---

## Self-Assessment Answer Key

1. `sort | uniq -c | sort -rn`: sort groups identical lines together, `uniq -c` counts each group, `sort -rn` ranks by count (highest first).

2. A port scan. The IP with 80 attempts is probing many different destination ports. The high count relative to normal traffic (6-12) and the fact that all are DENY confirms unauthorized reconnaissance.

3. `tshark -r capture.pcap -Y 'http.request.method == "POST"'`

4. Two things: (1) malware C2 communication; the workstation is infected and checking in with an attacker-controlled domain, and (2) data exfiltration; the random hex subdomains encode stolen data being smuggled out through DNS.

5. "Failed password for admin" means the username "admin" exists on the system but the password was wrong. "Failed password for invalid user admin" means the username "admin" does not exist at all. The distinction between the two messages tells the attacker which usernames are valid.

6. Check whether any login from that IP succeeded (`grep "SUSPICIOUS_IP" auth.log | grep "Accepted"`). If you find an accepted login, the attacker gained access and the incident is far more serious than a failed brute-force attempt.
