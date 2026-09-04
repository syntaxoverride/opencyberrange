# Failed Login Attempt Analysis - Solution Walkthrough

## Lab Overview

In this lab, you'll investigate SSH authentication logs from MediCare Regional Hospital's server to identify a brute-force attack. You'll learn to recognize attack patterns, count failed login attempts, and differentiate malicious activity from legitimate user errors.

## Learning Objectives

- Understand SSH authentication log format
- Identify brute-force attack patterns
- Use command-line tools to analyze logs
- Count failed attempts per IP address
- Document security incidents

## Scenario

Marcus Thompson, MediCare's CISO, has received automated alerts about unusual failed SSH login attempts on a critical server. Your job is to analyze the authentication logs and determine if this is a brute-force attack or just normal failed login activity.

## Solution Walkthrough

### Step 1: Access the Authentication Logs

The SSH authentication logs are served via HTTP from the lab container:

```bash
# Download the logs locally
curl http://10.100.{user_id}.10/auth.log -o auth.log

# Or view in browser
http://10.100.{user_id}.10/auth.log
```

### Step 2: Understand the Log Format

SSH authentication logs follow a standard format:

```
Jan 15 08:15:23 medicare-ssh sshd[12345]: Accepted password for jthompson from 10.50.1.15 port 54321 ssh2
Jan 15 11:23:45 medicare-ssh sshd[23456]: Failed password for admin from 185.220.101.77 port 49152 ssh2
Jan 15 11:23:52 medicare-ssh sshd[23457]: Failed password for invalid user root from 185.220.101.77 port 49153 ssh2
```

**Key components:**
- **Timestamp**: When the authentication attempt occurred
- **Hostname**: medicare-ssh (the server)
- **Process**: sshd[PID] - SSH daemon with process ID
- **Result**: "Accepted password" (success) or "Failed password" (failure)
- **Username**: The account being accessed
- **Invalid user**: Indicates the username doesn't exist on the system
- **Source IP**: Where the connection came from
- **Port**: Source port (client side)

### Step 3: Search for Failed Login Attempts

Let's find all failed authentication attempts:

```bash
# Show all failed password attempts
grep "Failed password" auth.log

# Count total failed attempts
grep "Failed password" auth.log | wc -l
```

You should see a mix of:
- Occasional failures from hospital IPs (10.50.x.x) - legitimate typos
- Many failures from an external IP - potential attack

### Step 4: Count Failed Attempts by IP Address

Identify which IP addresses have the most failed login attempts:

```bash
# Extract and count source IPs from failed attempts
grep "Failed password" auth.log | grep -oE "from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | \
  awk '{print $2}' | sort | uniq -c | sort -rn
```

**Expected output:**
```
     60 185.220.101.77
      2 10.50.1.15
      1 10.50.2.8
      1 10.50.3.12
```

The external IP `185.220.101.77` has **60 failed attempts** - a clear sign of brute-force attack!

**Normal vs. Malicious:**
- **Hospital staff IPs** (10.50.x.x): 0-2 failures (typos, followed by successful login)
- **Attacker IP** (185.220.101.77): 60 failures, no successes

### Step 5: Analyze the Attacker's Activity

Examine all authentication attempts from the suspicious IP:

```bash
# Show all attempts from the attacker
grep "185.220.101.77" auth.log | grep "Failed password"
```

**What you'll observe:**
- All attempts are failures (no "Accepted password" entries)
- Rapid succession (attempts seconds apart)
- Many different usernames tried
- Mix of valid and invalid usernames

### Step 6: Identify Usernames Targeted

See what usernames the attacker tried:

```bash
# Extract usernames from attacker's attempts
grep "185.220.101.77" auth.log | grep "Failed password" | \
  awk '{for(i=1;i<=NF;i++) if($i=="for") print $(i+1), $(i+2)}' | sort -u
```

**Typical brute-force usernames:**
```
admin
root
user
test
guest
administrator
postgres
mysql
ubuntu
jenkins
backup
...
```

These are **dictionary usernames** - common account names that attackers try across many systems.

### Step 7: Examine Attack Timeline

Check when the attack occurred:

```bash
# Show timestamps of attacker's attempts
grep "185.220.101.77" auth.log | grep "Failed password" | awk '{print $1, $2, $3}' | head
grep "185.220.101.77" auth.log | grep "Failed password" | awk '{print $1, $2, $3}' | tail
```

The attack happens over a short period (10-15 minutes), with attempts every 8-15 seconds.

**Attack pattern:**
- **Duration**: ~10-15 minutes
- **Frequency**: 4-7 attempts per minute
- **Total attempts**: 60 failed logins
- **Success rate**: 0% (all attempts failed)

### Step 8: Find the Flag

The flag is embedded in the security analysis comments in the log file. Look for comment lines (starting with #) related to the attack:

```bash
# Find comment lines in the log
grep "^#" auth.log

# Search for the flag directly
grep "OCR{" auth.log
```

**You'll find:**
```
# Jan 15 11:38:45 SECURITY ANALYSIS COMPLETE
# Attack detected from 185.220.101.77
# Total failed attempts: 60
# Unique usernames tried: 57
# Attack pattern: Dictionary-based SSH brute-force
# Recommendation: Block IP immediately, review fail2ban configuration
# Flag: OCR{brut3_f0rc3_d3t3ct3d}
```

**Flag:** `OCR{brut3_f0rc3_d3t3ct3d}`

## Attack Analysis Summary

### Brute-Force Attack Characteristics

**Attacker Information:**
- **Source IP**: 185.220.101.77 (external, non-hospital IP)
- **Attack type**: Dictionary-based SSH brute-force
- **Duration**: Approximately 10-15 minutes
- **Total attempts**: 60 failed password attempts
- **Usernames tried**: 57 unique usernames (admin, root, user, test, etc.)
- **Success rate**: 0% (all attempts blocked)

**Attack Pattern:**
1. Rapid successive login attempts (8-15 seconds apart)
2. Dictionary of common usernames
3. Mix of valid and invalid user accounts
4. All attempts from single external IP
5. No successful authentications

**Indicators of Compromise (IoCs):**
- ✓ High volume of failures from single IP (60 attempts)
- ✓ Multiple invalid usernames
- ✓ Rapid succession (seconds between attempts)
- ✓ External/foreign IP address
- ✓ Common/default username attempts

### Defensive Recommendations

**Immediate Actions:**
1. **Block the attacker IP**: 185.220.101.77
2. **Review successful logins**: Ensure no compromise occurred
3. **Alert security team**: Document and report incident

**Long-term Prevention:**
1. **Implement fail2ban**: Automatically block IPs after 3-5 failed attempts
2. **Use SSH keys instead of passwords**: Much stronger authentication
3. **Disable root login**: Prevent root SSH access entirely
4. **Change default SSH port**: Reduce automated attacks
5. **Enable two-factor authentication (2FA)**: Add extra security layer
6. **Implement IP allowlisting**: Only allow SSH from known IPs
7. **Monitor auth logs continuously**: Set up alerts for attack patterns
8. **Use strong password policies**: If passwords are required

## Key Takeaways

### Log Analysis Techniques

**Finding attacks in logs:**
```bash
# 1. Count failures per IP
grep "Failed password" auth.log | grep -oE "from [0-9.]+" | awk '{print $2}' | sort | uniq -c | sort -rn

# 2. Analyze specific IP
grep "SUSPICIOUS_IP" auth.log

# 3. Extract attempted usernames
grep "SUSPICIOUS_IP" auth.log | grep -oE "for (invalid user )?[a-z0-9]+" | sort -u

# 4. Check attempt timing
grep "SUSPICIOUS_IP" auth.log | awk '{print $1, $2, $3}'
```

### Recognizing Brute-Force Patterns

**Red flags:**
- 10+ failed attempts from same IP
- Invalid/unknown usernames
- Common dictionary names (admin, root, test)
- Rapid succession (seconds/minutes)
- External/unexpected IP addresses
- No successful logins despite many attempts

**Normal behavior:**
- 0-2 failures (typos) followed by success
- Known internal IP addresses
- Legitimate usernames
- Reasonable time between attempts

### Real-World Application

This type of attack is **extremely common**:
- SSH brute-force attacks occur constantly on internet-facing servers
- Automated bots scan for exposed SSH ports (default port 22)
- Attackers use huge password dictionaries
- Many organizations face thousands of attempts daily

**Industry best practices:**
- Never expose SSH directly to the internet
- Always use VPN or bastion hosts for SSH access
- Implement automated blocking (fail2ban, Cloudflare)
- Monitor authentication logs continuously
- Use SSH keys instead of passwords

## Additional Analysis Commands

### Advanced Log Analysis

```bash
# Count total authentication events
wc -l auth.log

# Find all successful logins
grep "Accepted password" auth.log

# List all unique source IPs
grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" auth.log | sort -u

# Count invalid user attempts
grep "invalid user" auth.log | wc -l

# Find most commonly attempted usernames
grep "Failed password" auth.log | awk '{for(i=1;i<=NF;i++) if($i=="for") print $(i+1)}' | \
  grep -v "invalid" | sort | uniq -c | sort -rn | head -10

# Show attack timeline
grep "185.220.101.77" auth.log | grep "Failed password" | awk '{print $1, $2, $3}' | \
  uniq -c
```

### Visualization

You could visualize this data:
- Create a bar chart of failed attempts per IP
- Plot timeline of attack showing attempt frequency
- Map geographic location of attacker IP
- Graph username distribution (what names were tried most)

## Conclusion

You successfully identified and analyzed an SSH brute-force attack by:
1. ✓ Understanding SSH auth log format
2. ✓ Counting failed attempts per IP address
3. ✓ Identifying suspicious patterns (60 failures from one IP)
4. ✓ Analyzing attacker behavior (dictionary usernames, rapid attempts)
5. ✓ Differentiating malicious activity from legitimate failures
6. ✓ Documenting the attack and recommending defenses

**Skills acquired:**
- Log analysis with grep, awk, sort, uniq
- Pattern recognition in authentication logs
- Incident documentation and reporting
- Understanding of brute-force attack techniques
- Knowledge of SSH security best practices

**Flag:** `OCR{brut3_f0rc3_d3t3ct3d}`

---

**Lab created for MediCare Regional Hospital Security Training Program**

*Remember: This lab uses simulated data for educational purposes. In a real incident, you would also coordinate with your incident response team, preserve evidence, and follow your organization's security policies.*
