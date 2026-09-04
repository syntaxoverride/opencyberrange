# Multi-Service Discovery - Walkthrough

## Lab Overview

This lab teaches comprehensive service enumeration by scanning multiple ports simultaneously and then interacting with discovered services. You'll learn how to identify all services on a target, connect to them, and piece together information that may be distributed across multiple services.

**Difficulty**: Beginner
**Estimated Time**: 30-45 minutes

## Prerequisites

- Completion of "SSH Service Detection" lab
- Understanding of basic port scanning
- Familiarity with nmap

## Learning Objectives

By completing this lab, you will:
1. Scan multiple ports simultaneously
2. Enumerate different service types (FTP, SSH, HTTP)
3. Connect to FTP servers with anonymous access
4. Examine web server content and HTML source
5. Piece together information from different sources
6. Understand the importance of comprehensive enumeration

## Tools Needed

- **nmap**: Network scanning and service detection
- **ftp**: FTP client for file transfer
- **curl**: HTTP client (or web browser)

## Background

In real-world penetration testing, servers typically run multiple services:
- **Web servers**: HTTP/HTTPS + SSH for administration
- **File servers**: FTP/SMB + SSH for management
- **Database servers**: MySQL/PostgreSQL + SSH + management interfaces

**Why comprehensive enumeration matters:**
- Each service is a potential attack vector
- Information may be distributed across services
- Different services reveal different system details
- Complete attack surface requires examining all services
- Missing one service means missing potential vulnerabilities

## Step-by-Step Solution

### Step 1: Understand the Target

TechStart's Linux servers run multiple services for different purposes. Your goal is to identify ALL services and interact with them to gather complete information.

### Step 2: Multi-Port Scan

Scan common Linux service ports:

```bash
nmap -p 21,22,80 -sV 10.10.{user_id}.10
```

**Expected output:**
```
Starting Nmap 7.94
Nmap scan report for 10.10.{user_id}.10
Host is up (0.00050s latency).

PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.5
22/tcp open  ssh     OpenSSH 8.9p1 Ubuntu
80/tcp open  http    Apache httpd 2.4.52 ((Ubuntu))
Service Info: OS: Linux
```

**What this tells us:**
- Three services are running
- FTP (21) - File transfer, possibly anonymous access
- SSH (22) - Remote administration
- HTTP (80) - Web server

### Step 3: Investigate FTP Service (Part 1 of Flag)

FTP servers often allow anonymous access for public files. Try connecting:

```bash
ftp 10.10.{user_id}.10
```

**Login process:**
```
Connected to 10.10.{user_id}.10.
220 (vsFTPd 3.0.5)
Name: anonymous
331 Please specify the password.
Password: (just press Enter)
230 Login successful.
ftp>
```

**Explore the FTP server:**
```bash
ftp> ls
ftp> cd pub
ftp> ls
ftp> get readme.txt
ftp> quit
```

**View the downloaded file:**
```bash
cat readme.txt
```

**Contents:**
```
========================================
TechStart Inc. - File Transfer Server
========================================

Welcome to the TechStart FTP server.
For authorized file transfers only.

Flag Part 1: OCR{mult1_

Contact: admin@techstart.local
```

**Found Part 1:** `OCR{mult1_`

### Step 4: Investigate Web Server (Part 2 of Flag)

Check the web server content:

```bash
curl http://10.10.{user_id}.10/
```

**Output:**
```html
<!DOCTYPE html>
<html>
<head><title>TechStart Web Server</title></head>
<body>
<h1>Welcome to TechStart</h1>
<p>This is the internal web server for TechStart Inc.</p>
<!-- Development notes: Flag Part 2: s3rv1c3} -->
</body>
</html>
```

**Found Part 2:** `s3rv1c3}` (hidden in HTML comment)

### Step 5: Assemble the Complete Flag

Combine the parts found from both services:

- **Part 1 (FTP):** `OCR{mult1_`
- **Part 2 (HTTP):** `s3rv1c3}`

**Complete flag:** `OCR{mult1_s3rv1c3}`

## Key Takeaways

### Why This Lab Design Matters

This lab intentionally splits the flag across multiple services to teach a critical lesson:

**In real penetration tests:**
- Critical information is often scattered across multiple services
- Focusing on just one service results in incomplete intelligence
- Each service provides unique information
- Complete picture requires examining ALL sources
- Comprehensive enumeration prevents missed opportunities

### The Danger of Incomplete Enumeration

**Bad practice:**
```bash
# Only scanning and checking SSH
nmap -p 22 -sV 10.10.{user_id}.10
```
Result: You'd miss FTP and HTTP entirely, losing all flag information.

**Good practice:**
```bash
# Scan all common services
nmap -p 21,22,80 -sV 10.10.{user_id}.10
# Then interact with each discovered service
ftp 10.10.{user_id}.10
curl http://10.10.{user_id}.10/
```
Result: Complete service landscape and all available information.

### Professional Enumeration Workflow

1. **Identify all open ports** - Don't skip services
2. **Version detection on ALL services** - Not just one or two
3. **Interact with services** - Connect, browse, download
4. **Examine all content** - Including HTML source, comments, hidden files
5. **Document systematically** - Record findings from each service
6. **Cross-reference** - Look for patterns and connections
7. **Piece together** - Combine information from multiple sources

## Common Mistakes and Troubleshooting

### Mistake 1: Scanning Only One Port

**Wrong:**
```bash
nmap -p 22 -sV 10.10.{user_id}.10
```

This only shows SSH. You completely miss FTP and HTTP.

**Right:**
```bash
nmap -p 21,22,80 -sV 10.10.{user_id}.10
```

### Mistake 2: Not Interacting with Services

**Wrong:**
Only running nmap and expecting all information in scan results.

**Right:**
After discovering services, connect to them:
- FTP: `ftp <target>` and browse/download files
- HTTP: `curl <target>` and examine HTML source

### Mistake 3: Missing HTML Comments

**Problem:**
- Student visits web page in browser
- Only sees rendered content
- Misses HTML comment containing flag part

**Solution:**
- Always view page source (Ctrl+U or Right-click → View Source)
- Use `curl` which shows raw HTML
- Look for `<!-- comments -->`

### Mistake 4: Not Using Anonymous FTP

**Problem:**
Student tries to log in with credentials and gives up.

**Solution:**
Try anonymous access first:
- Username: `anonymous`
- Password: (blank or any email)

## Additional Enumeration Techniques

### Option 1: Aggressive nmap Scan

```bash
nmap -p 21,22,80 -A 10.10.{user_id}.10
```

The `-A` flag combines version detection, OS detection, and scripts.

### Option 2: FTP with NSE Scripts

```bash
nmap -p 21 --script ftp-anon 10.10.{user_id}.10
```

Checks for anonymous FTP access automatically.

### Option 3: Web Enumeration

```bash
# Check robots.txt
curl http://10.10.{user_id}.10/robots.txt

# Directory enumeration
dirb http://10.10.{user_id}.10/
```

## Real-World Application

### Attack Surface Analysis

From this scan, a penetration tester would document:

**Service Inventory:**
| Port | Service | Version | Notes |
|------|---------|---------|-------|
| 21 | FTP | vsftpd 3.0.5 | Anonymous access enabled |
| 22 | SSH | OpenSSH 8.9p1 | Standard config |
| 80 | HTTP | Apache 2.4.52 | Basic web server |

**Potential Attack Vectors:**
1. **FTP (21)**:
   - Anonymous access allows file browsing
   - Check for sensitive files
   - Test for write permissions

2. **SSH (22)**:
   - Attempt username enumeration
   - Check for weak credentials (if authorized)

3. **HTTP (80)**:
   - Source code review for comments/secrets
   - Directory enumeration
   - Web application vulnerabilities

## Defensive Recommendations

**Service Minimization:**
- Only run necessary services
- Disable anonymous FTP if not needed
- Reduces attack surface

**Information Disclosure:**
- Remove development comments from production HTML
- Configure FTP to hide sensitive files
- Review all public content for secrets

**Access Controls:**
- Restrict anonymous FTP access
- Use authentication where possible
- Implement IP-based restrictions

## Conclusion

You've successfully:
- ✅ Scanned multiple ports simultaneously
- ✅ Identified FTP, SSH, and HTTP services
- ✅ Connected to FTP with anonymous access
- ✅ Found hidden information in HTML comments
- ✅ Pieced together information from multiple sources
- ✅ Understood the critical importance of comprehensive enumeration

**Critical Lesson:**
In penetration testing, **comprehensive enumeration is essential**. Information is often distributed across multiple services. You must discover all services, interact with each one, and examine all available content to get the complete picture.

## References

- [Nmap Multi-Port Scanning](https://nmap.org/book/man-port-specification.html)
- [FTP Anonymous Access](https://book.hacktricks.xyz/network-services-pentesting/pentesting-ftp)
- [Web Source Code Analysis](https://owasp.org/www-project-web-security-testing-guide/)
