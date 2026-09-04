# Non-Standard Port Discovery - Walkthrough

## Lab Overview

This lab teaches comprehensive port scanning techniques to discover services running on non-standard ports. You'll learn how to perform extended port range scans, identify services on non-standard ports, access web servers to gather information, and connect to SSH services using discovered credentials.

**Difficulty**: Beginner
**Estimated Time**: 30-45 minutes

## Prerequisites

- Basic understanding of networking and ports
- Familiarity with nmap fundamentals
- Understanding of common service ports (SSH: 22, HTTP: 80, HTTPS: 443)
- Kali Linux with nmap installed (pre-installed by default)

## Learning Objectives

By completing this lab, you will:
1. Understand security through obscurity and non-standard ports
2. Recognize the limitations of default port scans
3. Perform extended port range scanning with nmap
4. Use efficient scanning strategies to discover hidden services
5. Identify services regardless of their configured port numbers
6. Access web servers on non-standard ports to gather information
7. Use discovered credentials to connect to SSH on non-standard ports

## Tools Needed

- **nmap**: Network scanning and service detection tool (pre-installed on Kali)
- **curl** or **web browser**: To access the web server and view credentials
- **ssh**: SSH client to connect to the server (pre-installed on Kali)

## Background

### Security Through Obscurity

Administrators sometimes configure services on non-standard ports as a "security through obscurity" measure:

**Common examples:**
- SSH on port 2222 instead of 22
- Web servers on port 8080 instead of 80
- HTTPS on port 8443 instead of 443
- Databases on custom ports

**Why administrators do this:**
- Reduce automated attacks (bots scan common ports)
- Hide from casual scans
- Compliance requirements
- Run multiple instances of the same service
- Organizational security policies

**Security limitations:**
- Doesn't fix actual vulnerabilities
- Easily discovered with proper scanning
- Provides no real security
- May give false sense of protection

### Port Scanning Strategies

**Default nmap scan:**
- Scans ~1000 most common ports
- Fast but may miss services
- Good for initial reconnaissance

**Extended port scans:**
- `-p 1-10000`: First 10,000 ports (partial coverage)
- `-p-`: All 65,535 ports (comprehensive but slow)
- `--top-ports N`: Top N most common ports

**Best practice:**
Start with default scans for speed, then use `-p-` when thoroughness is critical; services can hide on any port above 10,000.

## Step-by-Step Solution

### Step 1: Verify Target Connectivity

First, ensure you can reach the target server:

```bash
ping -c 3 10.10.{user_id}.10
```

**Expected output:**
```
64 bytes from 10.10.{user_id}.10: icmp_seq=1 ttl=64 time=0.123 ms
```

### Step 2: Default Port Scan (Will Miss Services)

Start with a default scan to see what's normally visible:

```bash
nmap 10.10.{user_id}.10
```

**Expected output:**
```
Starting Nmap 7.94
Nmap scan report for 10.10.{user_id}.10
Host is up (0.00050s latency).
Not shown: 999 closed tcp ports (conn-refused)

PORT   STATE SERVICE
(all ports filtered or closed)
```

**What this tells us:**
- Default scan checks ~1000 most common ports
- Port 34567 (HTTP) is NOT in the default scan range
- Port 22222 (SSH) is NOT in the default scan range
- Both services are completely missed!

### Step 3: Extended Port Range Scan

To discover services on non-standard ports, scan all ports:

```bash
nmap -p- -T4 10.10.{user_id}.10
```

**Expected output:**
```
Starting Nmap 7.94
Nmap scan report for 10.10.{user_id}.10
Host is up (0.00050s latency).
Not shown: 65533 closed tcp ports (conn-refused)

PORT      STATE SERVICE
34567/tcp open  dhanalakshmi
22222/tcp open  easyengine
```

**What this tells us:**
- Scanned all 65,535 ports
- Discovered port 34567 (HTTP on non-standard port!)
- Discovered port 22222 (SSH on non-standard port!)
- Services identified with generic names (need version detection)

### Step 4: Service Version Detection

To identify what's actually running on these ports:

```bash
nmap -p- -sV -T4 10.10.{user_id}.10
```

**Expected output:**
```
Starting Nmap 7.94
Nmap scan report for 10.10.{user_id}.10
Host is up (0.00052s latency).
Not shown: 65533 closed tcp ports (conn-refused)

PORT      STATE SERVICE VERSION
34567/tcp open  http    Apache httpd 2.4.41 ((Ubuntu))
22222/tcp open  ssh     OpenSSH 8.2p1 Ubuntu-4ubuntu0.5

Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results.
Nmap done: 1 IP address (1 host up) scanned in 15.32 seconds
```

**What this tells us:**
- **Port 34567**: Apache web server (non-standard HTTP port!)
- **Port 22222**: SSH service (non-standard port!)
- Both services are on non-standard ports
- HTTP normally runs on port 80, but here it's on 34567
- SSH normally runs on port 22, but here it's on 22222

### Step 5: Access the Web Server

Visit the web server to gather information:

```bash
curl http://10.10.{user_id}.10:34567
```

Or open in a browser: `http://10.10.{user_id}.10:34567`

**What you'll see:**
A professional engineering demo page displaying:
- SSH Port: **22222**
- Username: **techstart**
- Password: **TechStart2024#**

This page is styled as an internal engineering testing environment, showing credentials for the test SSH server.

### Step 6: Connect to SSH and Capture the Flag

Use the credentials from the web page to connect to SSH:

```bash
ssh -p 22222 techstart@10.10.{user_id}.10
```

**When prompted for password, enter:** `TechStart2024#`

**After connecting, retrieve the flag:**

```bash
cat flag.txt
```

**Expected output:**
```
OCR{n0n_st4nd4rd}
```

**Key observations:**
- HTTP was hidden on port 34567 (non-standard)
- SSH was hidden on port 22222 (non-standard)
- Default scan completely missed both services
- A full port scan (`-p-`) found both ports
- Web server provided credentials needed for SSH access
- Connecting to SSH on non-standard port requires the `-p` flag
- Flag is stored in a file accessible after SSH login

## Key Takeaways

### Why Extended Scanning Matters

**Default scans are insufficient:**
- Only check ~1000 most common ports
- Miss services on non-standard ports
- Incomplete enumeration
- False sense of completeness

**Extended scans are necessary:**
- Discover services on any port
- Reveal security-through-obscurity configurations
- Ensure comprehensive assessment
- Find hidden attack surface

### Scanning Strategy Comparison

**Fast reconnaissance:**
```bash
nmap <target>
```
- Quick initial scan
- Checks common ports only
- May miss hidden services

**Extended range (partial coverage):**
```bash
nmap -p 1-40000 -sV <target>
```
- Scans first 40,000 ports
- Catches many non-standard configurations
- Note: still misses services on ports above 40,000
- Faster than a full scan

**Comprehensive scan (recommended for thoroughness):**
```bash
nmap -p- -sV <target>
```
- All 65,535 ports
- Guarantees nothing is missed
- Slow but complete

### Security Implications

From this scan, a penetration tester would document:

1. **Service Discovery:**
   - SSH accessible on port 22222 (non-standard)
   - HTTP accessible on port 34567 (non-standard)

2. **Security Through Obscurity:**
   - Both SSH and HTTP moved to non-standard ports
   - Provides no real security
   - Discovered easily with proper scanning
   - Web server exposes credentials (poor security practice)

3. **Version Information:**
   - OpenSSH 8.2p1 version disclosed
   - Ubuntu OS revealed
   - Can research for known vulnerabilities

4. **Service Access:**
   - SSH accessible on non-standard port
   - Requires connecting with `-p` flag to specify port
   - Flag accessible after authentication

## Common Mistakes and Troubleshooting

### Mistake 1: Using Default Scan Only

**Wrong:**
```bash
nmap 10.10.{user_id}.10
```

This only scans the top 1000 common ports. Ports 34567 and 22222 are not in this range, so both HTTP and SSH are completely missed.

**Right:**
```bash
nmap -p- -sV -T4 10.10.{user_id}.10
```

A full port scan ensures non-standard ports are discovered, even on high-numbered ports.

### Mistake 2: Scanning Without Version Detection

**Wrong:**
```bash
nmap -p- -T4 10.10.{user_id}.10
```

This finds ports 34567 and 22222 but doesn't identify what services are running.

**Right:**
```bash
nmap -p- -sV -T4 10.10.{user_id}.10
```

The `-sV` flag is essential for service identification. This reveals HTTP on 34567 and SSH on 22222.

### Mistake 3: Not Accessing the Web Server

**Wrong:**
Discovering HTTP on port 34567 but not visiting the web page.

**Right:**
After discovering HTTP on port 34567, visit it to gather information:
```bash
curl http://10.10.{user_id}.10:34567
```
or open in browser: `http://10.10.{user_id}.10:34567`

The web page contains the SSH credentials needed for access.

### Mistake 4: Not Connecting to SSH

**Wrong:**
Only scanning and not connecting to discovered services.

**Right:**
After discovering SSH on port 22222 and obtaining credentials from the web page, connect to it:
```bash
ssh -p 22222 techstart@10.10.{user_id}.10
```

Then retrieve the flag from the file:
```bash
cat flag.txt
```

### Mistake 5: Scanning Too Narrow a Range

**Insufficient:**
```bash
nmap -p 1-1000 10.10.{user_id}.10  # Misses ports 22222 and 34567
```

**Still insufficient:**
```bash
nmap -p 1-10000 10.10.{user_id}.10  # Still misses both ports (22222 and 34567 are above 10,000)
```

**Correct:**
```bash
nmap -p- -T4 10.10.{user_id}.10  # Scans all 65,535 ports; nothing is missed
```

## Alternative Approaches

### Targeted Port Range

If you know common alternative ports:

```bash
nmap -p 80,8080,443,34567,22,2222,22222 -sV 10.10.{user_id}.10
```

This quickly checks common HTTP and SSH port alternatives.

### Full Port Scan

For absolute certainty:

```bash
nmap -p- -sV 10.10.{user_id}.10
```

Scans all 65,535 ports. Slow but guaranteed to find everything.

### Faster Extended Scan

Use timing options to speed up extended scans:

```bash
nmap -p- -sV -T4 10.10.{user_id}.10
```

The `-T4` flag uses more aggressive timing for faster results.

### Top Ports Approach

Scan the most common ports including some alternatives:

```bash
nmap --top-ports 5000 -sV 10.10.{user_id}.10
```

Checks top 5000 most common ports (includes 2222).

## Real-World Application

### Common Non-Standard Port Patterns

**SSH alternatives:**
- 2222, 22222, 2022, 2200
- Very common in production environments

**HTTP alternatives:**
- 8000, 8080, 8888, 3000, 4000, 5000
- Common for web applications and APIs

**HTTPS alternatives:**
- 8443, 4443, 9443
- Administrative interfaces

**Database alternatives:**
- MySQL: 33060 instead of 3306
- PostgreSQL: 54320 instead of 5432
- MongoDB: 27018 instead of 27017

### Penetration Testing Best Practices

1. **Always scan extended port ranges**
   - Don't rely on default scans
   - Services can be on any port

2. **Use service version detection**
   - Confirms service identity
   - Reveals version information
   - Provides security-relevant data

3. **Document non-standard configurations**
   - Note which services are on non-standard ports
   - Explain why (if known)
   - Assess security impact

4. **Test the same attacks**
   - Port number doesn't change vulnerabilities
   - SSH on 2222 has same risks as SSH on 22
   - Don't assume non-standard = secure

## Defensive Recommendations

As a penetration tester, you might recommend:

1. **Don't rely on port obscurity**
   - Changing ports doesn't fix vulnerabilities
   - Provides no real security benefit
   - Creates false sense of protection

2. **If non-standard ports are used**
   - Understand it's not a security control
   - Still implement proper authentication
   - Keep services patched and updated
   - Use strong configurations

3. **Better security measures**
   - Strong authentication (key-based for SSH)
   - Network segmentation
   - Firewall rules limiting access
   - Intrusion detection/prevention
   - Regular security updates

4. **Banner configuration**
   - Minimize information disclosure
   - Remove version details from banners
   - Don't include sensitive information
   - Keep banners generic

## Conclusion

You've successfully:
- ✅ Discovered the limitations of default port scans
- ✅ Performed extended port range scanning
- ✅ Identified HTTP on a non-standard port (34567)
- ✅ Identified SSH on a non-standard port (22222)
- ✅ Used service version detection to confirm service identity
- ✅ Accessed the web server to gather credentials
- ✅ Connected to SSH on a non-standard port using `-p` flag
- ✅ Captured the flag by accessing the file via SSH
- ✅ Understood that security through obscurity is ineffective

This skill is essential for comprehensive penetration testing. Always scan beyond default ports to ensure complete service discovery.

## References

- [Nmap Port Specification](https://nmap.org/book/man-port-specification.html)
- [Nmap Version Detection](https://nmap.org/book/man-version-detection.html)
- [Security Through Obscurity](https://en.wikipedia.org/wiki/Security_through_obscurity)
- [Common Port Assignments (IANA)](https://www.iana.org/assignments/service-names-port-numbers/)
