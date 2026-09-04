# SSH Service Detection - Walkthrough

## Lab Overview

This lab teaches the fundamentals of SSH service detection using nmap. You'll learn how to identify SSH services, gather version information, and understand the importance of service enumeration in penetration testing.

**Difficulty**: Beginner
**Estimated Time**: 30-45 minutes

## Prerequisites

- Basic understanding of networking concepts
- Familiarity with command-line interfaces
- Kali Linux with nmap installed (pre-installed by default)

## Learning Objectives

By completing this lab, you will:
1. Understand what SSH is and why it's important in security assessments
2. Use nmap for basic port scanning
3. Perform service version detection
4. Interpret nmap scan results
5. Identify security-relevant information from SSH banners

## Tools Needed

- **nmap**: Network scanning and service detection tool (pre-installed on Kali)

## Background

SSH (Secure Shell) is the standard protocol for secure remote access to Linux/Unix systems. It provides:
- Encrypted communication
- Authentication (password and/or public key)
- Remote command execution
- File transfer capabilities

For penetration testers, SSH is critical because:
- It's the primary remote access method for Linux servers
- Outdated versions may have known vulnerabilities
- Misconfigured SSH can allow unauthorized access
- SSH version reveals OS information

## Step-by-Step Solution

### Step 1: Discover and Verify the Target

The platform provides your lab network subnet. First, scan the subnet to discover the target:

```bash
nmap -sn <network_subnet>
```

Identify the target IP from the scan results, then verify connectivity:

```bash
ping -c 3 <target_ip>
```

**Expected output:**
```
64 bytes from <target_ip>: icmp_seq=1 ttl=64 time=0.123 ms
```

### Step 2: Basic Port Scan

Scan for SSH on the default port (TCP 22):

```bash
nmap -p 22 10.10.{user_id}.10
```

**Expected output:**
```
Starting Nmap 7.94
Nmap scan report for 10.10.{user_id}.10
Host is up (0.00050s latency).

PORT   STATE SERVICE
22/tcp open  ssh
```

**What this tells us:**
- Port 22 is open (listening for connections)
- The service is likely SSH (based on port number)
- The target accepts SSH connections

### Step 3: Service Version Detection (Critical)

To get detailed version information and confirm it's SSH:

```bash
nmap -p 22 -sV 10.10.{user_id}.10
```

**Expected output:**
```
Starting Nmap 7.94
Nmap scan report for 10.10.{user_id}.10
Host is up (0.00050s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1 Ubuntu-4ubuntu0.5 (Ubuntu Linux; protocol 2.0; flag: OCR{ssh_d3t3ct3d})

Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

**What this tells us:**
- **Service**: Confirmed as SSH
- **Version**: OpenSSH 8.2p1
- **OS**: Ubuntu Linux
- **Protocol**: SSH protocol 2.0
- **Flag**: OCR{ssh_d3t3ct3d} (embedded in banner)

### Step 4: Capture the Flag

The flag is visible in the service banner from step 3:

```
OCR{ssh_d3t3ct3d}
```

**Alternative method - Direct banner grab:**

You can also grab the SSH banner using netcat:

```bash
nc 10.10.{user_id}.10 22
```

This will display the SSH banner directly, though nmap's `-sV` provides more structured output.

## Key Takeaways

### Why Version Detection Matters

The `-sV` flag is critical because:
1. **Confirms service identity**: Port 22 could theoretically run other services
2. **Reveals version**: Specific version numbers can be checked against vulnerability databases
3. **Shows OS information**: "Ubuntu-4ubuntu0.5" tells us the underlying OS
4. **Exposes banners**: Custom banners may contain useful information

### Security Implications

From this scan, a penetration tester would note:
- SSH is publicly accessible
- The specific version (OpenSSH 8.2p1) can be researched for CVEs
- The OS version is revealed (information disclosure)
- The custom banner contains a flag (poor operational security)

### Next Steps in Real Assessments

After SSH detection, typical next steps would be:
1. Check for known vulnerabilities in OpenSSH 8.2p1
2. Attempt to enumerate valid usernames
3. Test for weak authentication (if authorized)
4. Check SSH configuration for misconfigurations

## Common Mistakes and Troubleshooting

### Mistake 1: Scanning Without Version Detection

**Wrong:**
```bash
nmap -p 22 10.10.{user_id}.10
```

This only confirms port 22 is open, not that it's SSH or what version.

**Right:**
```bash
nmap -p 22 -sV 10.10.{user_id}.10
```

The `-sV` flag is essential for identifying the service and version.

### Mistake 2: Not Reading the Entire Output

The flag appears in the VERSION field of nmap output. Make sure to read all output carefully:
- Don't just look for "open" or "closed"
- Version information often contains critical details
- Service banners may reveal unexpected information

### Mistake 3: Not Scanning for the Target

The platform provides your network subnet; you must scan to discover the target IP:
- **Wrong**: Guessing an IP like `<target_ip>` without scanning first
- **Right**: Use `nmap -sn <network_subnet>` to discover the target, then use the discovered `<target_ip>` in your commands

## Additional Commands

### Comprehensive SSH Enumeration

For more detailed SSH information:

```bash
nmap -p 22 -sV -sC 10.10.{user_id}.10
```

The `-sC` flag runs default NSE scripts, which may reveal:
- Supported authentication methods
- SSH host keys
- Available encryption algorithms

### SSH-Specific NSE Scripts

To run all SSH-related scripts:

```bash
nmap -p 22 --script ssh-* 10.10.{user_id}.10
```

This runs specialized SSH enumeration scripts like:
- `ssh-auth-methods`: Shows supported authentication types
- `ssh-hostkey`: Displays the SSH host key
- `ssh2-enum-algos`: Lists supported encryption algorithms

## Defensive Recommendations

As a penetration tester, you might recommend:
1. **Customize SSH banner**: Remove version information to reduce information disclosure
2. **Update regularly**: Ensure SSH is patched against known vulnerabilities
3. **Disable root login**: Prevent direct root access via SSH
4. **Use key-based authentication**: Disable password authentication when possible
5. **Implement rate limiting**: Prevent brute-force attacks (fail2ban)
6. **Change default port**: Move SSH to non-standard port (security through obscurity)

## Conclusion

You've successfully:
- ✅ Detected an SSH service using nmap
- ✅ Identified the SSH version and OS
- ✅ Understood the importance of version detection
- ✅ Captured the flag from the service banner

This foundational skill is the first step in Linux penetration testing. Every Linux assessment begins with service detection to understand what's running and where to focus efforts.

## References

- [Nmap Official Documentation](https://nmap.org/book/man.html)
- [OpenSSH Security Advisories](https://www.openssh.com/security.html)
- [SSH Protocol Specification (RFC 4253)](https://tools.ietf.org/html/rfc4253)
