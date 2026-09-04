# NSE Script Enumeration - Walkthrough

## Lab Overview

This lab teaches advanced enumeration using Nmap's NSE (Nmap Scripting Engine). You'll learn how to use specialized scripts to gather detailed service information beyond basic version detection, specifically focusing on SSH enumeration.

**Difficulty**: Intermediate
**Estimated Time**: 60-90 minutes

## Prerequisites

- Completion of basic Linux enumeration labs (linux-1-1 through linux-1-4)
- Understanding of nmap basic scanning techniques
- Familiarity with SSH service
- Knowledge of service version detection (`-sV` flag)

## Learning Objectives

By completing this lab, you will:
1. Understand the Nmap Scripting Engine (NSE) and its capabilities
2. Learn to use NSE scripts for deep service enumeration
3. Execute SSH-specific NSE scripts
4. Analyze and interpret NSE script output
5. Gather comprehensive service configuration details
6. Understand the difference between basic and deep enumeration

## Tools Needed

- **nmap**: Network scanning tool with NSE capabilities (pre-installed on Kali)
  - Version 7.80 or higher recommended for full NSE functionality

## Background

### What is NSE?

The Nmap Scripting Engine (NSE) is a powerful feature of nmap that extends basic port scanning with:
- **Specialized scripts** for hundreds of services and vulnerabilities
- **Automated enumeration** that goes beyond simple version detection
- **Service-specific intelligence** gathering
- **Vulnerability detection** and security assessment capabilities

### Why NSE Matters

**Basic scan limitations:**
```bash
nmap -p 22 -sV <target>
# Output: "22/tcp open ssh OpenSSH 8.2p1"
```
This tells you SSH is running, but not much else.

**NSE script advantages:**
```bash
nmap -p 22 --script=ssh-auth-methods <target>
# Output: Shows authentication methods, configuration details, custom messages
```
This reveals authentication options, security settings, and detailed configuration.

### NSE Script Categories

- **default**: Safe scripts that run with `-sC`
- **auth**: Authentication testing
- **brute**: Brute force attacks
- **discovery**: Service and host discovery
- **exploit**: Exploitation attempts
- **vuln**: Vulnerability detection
- **safe**: Non-intrusive scripts

### SSH-Specific NSE Scripts

- `ssh-hostkey`: Retrieves SSH host keys and algorithms
- `ssh-auth-methods`: Enumerates supported authentication methods
- `ssh2-enum-algos`: Lists encryption algorithms and ciphers
- `sshv1`: Detects deprecated SSH version 1

## Step-by-Step Solution

### Step 1: Verify Target Connectivity

First, confirm you can reach the target:

```bash
ping -c 3 10.10.{user_id}.10
```

**Expected output:**
```
64 bytes from 10.10.{user_id}.10: icmp_seq=1 ttl=64 time=0.123 ms
```

### Step 2: Basic SSH Service Detection

Start with basic service detection to establish a baseline:

```bash
nmap -p 22 -sV 10.10.{user_id}.10
```

**Expected output:**
```
Starting Nmap 7.94
Nmap scan report for 10.10.{user_id}.10
Host is up (0.00050s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1 Ubuntu-4ubuntu0.5

Nmap done: 1 IP address (1 host up) scanned in 1.23 seconds
```

**What this tells us:**
- SSH is running on port 22
- Version is OpenSSH 8.2p1
- Operating system is Ubuntu

**What's missing:**
- Authentication methods supported
- SSH host keys and algorithms
- Encryption ciphers available
- Server configuration details
- **The flag!**

### Step 3: Understanding NSE Script Syntax

Before running NSE scripts, understand the syntax:

**Run specific script:**
```bash
nmap --script=<script-name> <target>
```

**Run multiple scripts:**
```bash
nmap --script=script1,script2 <target>
```

**Run all scripts matching pattern:**
```bash
nmap --script="ssh*" <target>
```

**Run default scripts:**
```bash
nmap -sC <target>
# Equivalent to: nmap --script=default <target>
```

### Step 4: SSH Host Key Enumeration

Retrieve SSH host keys and algorithms:

```bash
nmap -p 22 --script=ssh-hostkey 10.10.{user_id}.10
```

**Expected output:**
```
PORT   STATE SERVICE
22/tcp open  ssh
| ssh-hostkey:
|   2048 aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99 (RSA)
|   ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDGj7...
|   256 11:22:33:44:55:66:77:88:99:aa:bb:cc:dd:ee:ff:00 (ECDSA)
|   ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzd...
|   256 99:88:77:66:55:44:33:22:11:00:ff:ee:dd:cc:bb:aa (ED25519)
|_  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG8zRaB...
```

**Analysis:**
- **RSA key**: 2048-bit (secure, industry standard)
- **ECDSA key**: 256-bit elliptic curve
- **ED25519 key**: 256-bit modern algorithm (most secure)

### Step 5: SSH Authentication Methods Enumeration (Critical)

This is the key script that reveals the flag:

```bash
nmap -p 22 --script=ssh-auth-methods 10.10.{user_id}.10
```

**Expected output:**
```
PORT   STATE SERVICE
22/tcp open  ssh
| ssh-auth-methods:
|   Supported authentication methods:
|     password
|     publickey
|   TechStart SSH Server - Secure Access Only
|_  Enumeration flag: OCR{nse_scr1pt}
```

**Analysis:**
- **password**: Password authentication is enabled (allows brute force)
- **publickey**: Public key authentication is supported
- **Custom message**: Server identifies as "TechStart SSH Server"
- **Flag**: `OCR{nse_scr1pt}` appears in the script output!

### Step 6: Comprehensive SSH Enumeration (Alternative)

You can also run all SSH-related scripts at once:

```bash
nmap -p 22 --script="ssh*" 10.10.{user_id}.10
```

This runs:
- `ssh-hostkey`
- `ssh-auth-methods`
- `ssh2-enum-algos`
- And any other SSH-related NSE scripts

**Expected output:**
```
PORT   STATE SERVICE
22/tcp open  ssh
| ssh-hostkey:
|   [host key information]
| ssh-auth-methods:
|   Supported authentication methods:
|     password
|     publickey
|   TechStart SSH Server - Secure Access Only
|_  Enumeration flag: OCR{nse_scr1pt}
| ssh2-enum-algos:
|   [algorithm information]
```

### Step 7: Capture the Flag

The flag is revealed in the NSE script output:

```
OCR{nse_scr1pt}
```

**Flag location**:
- Script: `ssh-auth-methods`
- Line: `Enumeration flag: OCR{nse_scr1pt}`
- Context: Appears after supported authentication methods

## Key Takeaways

### NSE Provides Depth

**Basic version scan:**
- Shows: "SSH 8.2p1 is running"
- Missing: Authentication methods, configuration, detailed settings

**NSE script scan:**
- Shows: Authentication methods (password, publickey)
- Shows: Host keys and algorithms
- Shows: Custom server messages
- **Shows: The flag!**

### Service-Specific Scripts

Each service has specialized NSE scripts:

**SSH scripts:**
- `ssh-hostkey`: Host key information
- `ssh-auth-methods`: Authentication options
- `ssh2-enum-algos`: Encryption algorithms

**HTTP scripts:**
- `http-enum`: Directory enumeration
- `http-headers`: HTTP header analysis
- `http-methods`: Allowed HTTP methods

**SMB scripts:**
- `smb-enum-shares`: Share enumeration
- `smb-enum-users`: User listing
- `smb-os-discovery`: OS detection

### Reading NSE Output

NSE script output format:
```
PORT   STATE SERVICE
22/tcp open  ssh
| script-name:
|   Script output line 1
|   Script output line 2
|_  Script output line 3 (final line)
```

- Script name appears with `|` prefix
- Output is indented underneath
- Final line has `|_` prefix
- Multiple scripts create multiple sections

### Security Assessment Value

From this enumeration, we learned:

**Positive findings:**
- Strong cryptographic keys (RSA 2048, ED25519)
- Modern SSH version
- Supports secure public key authentication

**Security concerns:**
- Password authentication enabled (brute force possible)
- Custom banner reveals organization name
- Server configuration exposed

## Common Mistakes and Troubleshooting

### Mistake 1: Not Using NSE Scripts

**Wrong:**
```bash
nmap -p 22 -sV 10.10.{user_id}.10
```
Basic version detection won't reveal the flag.

**Right:**
```bash
nmap -p 22 --script=ssh-auth-methods 10.10.{user_id}.10
```
NSE scripts are required for deep enumeration.

### Mistake 2: Using Wrong NSE Script

**Less optimal:**
```bash
nmap -p 22 --script=ssh-hostkey 10.10.{user_id}.10
```
This shows host keys but not the flag.

**Better:**
```bash
nmap -p 22 --script=ssh-auth-methods 10.10.{user_id}.10
```
The flag appears in ssh-auth-methods output.

**Best:**
```bash
nmap -p 22 --script="ssh*" 10.10.{user_id}.10
```
Runs all SSH scripts for comprehensive enumeration.

### Mistake 3: Not Reading Complete Output

NSE scripts can produce lengthy output. Make sure to:
- Read all script output sections
- Look for custom messages
- Check for flags in script results
- Don't just skim for "open" or "closed"

### Mistake 4: Incorrect Script Syntax

**Wrong:**
```bash
nmap -p 22 --script ssh-auth-methods 10.10.{user_id}.10
```
Missing `=` after --script.

**Right:**
```bash
nmap -p 22 --script=ssh-auth-methods 10.10.{user_id}.10
```
Use `--script=<name>` format.

## Additional NSE Commands

### List Available NSE Scripts

See all NSE scripts on your system:
```bash
ls /usr/share/nmap/scripts/ | grep ssh
```

**Output:**
```
ssh-auth-methods.nse
ssh-brute.nse
ssh-hostkey.nse
ssh-publickey-acceptance.nse
ssh-run.nse
ssh2-enum-algos.nse
sshv1.nse
```

### View Script Documentation

Get help for any NSE script:
```bash
nmap --script-help ssh-auth-methods
```

**Output:**
```
ssh-auth-methods
Categories: auth safe
https://nmap.org/nsedoc/scripts/ssh-auth-methods.html
  Returns authentication methods that an SSH server supports.
```

### Run Default Scripts

Run all default (safe) scripts:
```bash
nmap -p 22 -sC 10.10.{user_id}.10
```

Equivalent to:
```bash
nmap -p 22 --script=default 10.10.{user_id}.10
```

### Combine Version Detection and Scripts

Best practice for comprehensive enumeration:
```bash
nmap -p 22 -sV -sC 10.10.{user_id}.10
```

- `-sV`: Version detection
- `-sC`: Default NSE scripts
- Combined: Maximum information gathering

## Real-World Applications

### Penetration Testing Workflow

**1. Port Discovery:**
```bash
nmap -p- --min-rate 10000 10.10.{user_id}.10
```

**2. Service Detection:**
```bash
nmap -p 22,80,445 -sV 10.10.{user_id}.10
```

**3. NSE Enumeration:**
```bash
nmap -p 22,80,445 -sC 10.10.{user_id}.10
```

**4. Service-Specific Scripts:**
```bash
nmap -p 22 --script="ssh*" 10.10.{user_id}.10
nmap -p 80 --script="http*" 10.10.{user_id}.10
nmap -p 445 --script="smb*" 10.10.{user_id}.10
```

### Vulnerability Assessment

Use `vuln` category scripts:
```bash
nmap --script=vuln 10.10.{user_id}.10
```

This runs all vulnerability detection scripts against the target.

### Brute Force Testing (Authorized Only)

NSE includes brute force scripts:
```bash
nmap --script=ssh-brute --script-args userdb=users.txt,passdb=passwords.txt <target>
```

**Warning**: Only use with explicit authorization!

## Defensive Recommendations

Based on this enumeration, recommendations for TechStart:

1. **Disable Password Authentication**
   - Configure SSH to use only public key authentication
   - Edit `/etc/ssh/sshd_config`: `PasswordAuthentication no`
   - Reduces brute force attack surface

2. **Customize SSH Banner**
   - Remove version information to reduce information disclosure
   - Use generic banner instead of organization name
   - Edit `/etc/ssh/sshd_config`: `Banner /etc/ssh/banner.txt`

3. **Implement Rate Limiting**
   - Use fail2ban to block brute force attempts
   - Configure iptables rate limiting
   - Monitor authentication logs

4. **Use Strong Key Algorithms**
   - Continue using ED25519 keys (already implemented)
   - Disable weak algorithms if any remain
   - Regular key rotation

5. **Network Segmentation**
   - Place SSH behind VPN or bastion host
   - Restrict SSH access to trusted IPs
   - Use port knocking for additional security

## Comparison: Basic vs NSE Scanning

### Basic Scan Output
```bash
$ nmap -p 22 -sV 10.10.{user_id}.10

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1
```

**Information gathered:**
- Port 22 is open
- Service is SSH
- Version is OpenSSH 8.2p1

**Information NOT gathered:**
- Authentication methods
- Host keys
- Configuration details
- Custom messages
- **NO FLAG**

### NSE Script Scan Output
```bash
$ nmap -p 22 --script=ssh-auth-methods 10.10.{user_id}.10

PORT   STATE SERVICE
22/tcp open  ssh
| ssh-auth-methods:
|   Supported authentication methods:
|     password
|     publickey
|   TechStart SSH Server - Secure Access Only
|_  Enumeration flag: OCR{nse_scr1pt}
```

**Information gathered:**
- Port 22 is open
- Service is SSH
- Authentication: password AND publickey
- Server identification: TechStart SSH Server
- Custom message present
- **FLAG FOUND**: OCR{nse_scr1pt}

### Value Added by NSE

NSE scripts add:
- **30% more enumeration time**
- **300% more useful information**
- **Critical security details** not visible in basic scans
- **Attack surface mapping** (authentication methods)
- **Flags and hidden messages** in service responses

## Conclusion

You've successfully:
- ✅ Understood the Nmap Scripting Engine (NSE)
- ✅ Used service-specific NSE scripts for SSH enumeration
- ✅ Executed ssh-hostkey and ssh-auth-methods scripts
- ✅ Analyzed NSE script output for security details
- ✅ Captured the flag from NSE script enumeration

### Critical Skills Learned

1. **NSE Basics**: Understanding script categories and usage
2. **Script Selection**: Choosing appropriate scripts for each service
3. **Output Analysis**: Interpreting NSE script results
4. **Deep Enumeration**: Going beyond basic port scanning
5. **Security Assessment**: Identifying configuration weaknesses

### Next Steps

After mastering NSE enumeration:
- Practice NSE scripts on other services (HTTP, SMB, FTP)
- Explore vulnerability detection scripts (`--script=vuln`)
- Learn to write custom NSE scripts (Lua language)
- Combine NSE with other enumeration tools
- Apply NSE in comprehensive penetration tests

## References

- [Nmap NSE Documentation](https://nmap.org/book/nse.html)
- [NSE Script Database](https://nmap.org/nsedoc/)
- [SSH Protocol Specification](https://tools.ietf.org/html/rfc4253)
- [OpenSSH Security](https://www.openssh.com/security.html)
- [Writing NSE Scripts](https://nmap.org/book/nse-tutorial.html)

## Advanced Exercises (Optional)

### Exercise 1: Discover All NSE Scripts
```bash
ls /usr/share/nmap/scripts/ | wc -l
```
How many NSE scripts are installed on your Kali system?

### Exercise 2: Enumerate HTTP Service
If TechStart also ran a web server, how would you enumerate it with NSE?
```bash
nmap -p 80 --script="http*" <target>
```

### Exercise 3: Vulnerability Scanning
How would you check for vulnerabilities across all services?
```bash
nmap --script=vuln <target>
```

### Exercise 4: Script Help
What does the ssh2-enum-algos script do?
```bash
nmap --script-help ssh2-enum-algos
```
