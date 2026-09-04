# Service Interaction - Walkthrough

## Lab Overview

This lab teaches you the limitations of port scanning and the importance of direct service interaction. You'll learn that some information is only visible when you actually connect to a service using its protocol client.

**Difficulty**: Beginner
**Estimated Time**: 20-30 minutes

## Prerequisites

- Understanding of port scanning (nmap)
- Completion of previous Linux Level 1 labs
- Basic knowledge of FTP

## Learning Objectives

1. Understand limitations of port scanning
2. Connect directly to services for deeper enumeration
3. Use FTP client for service interaction
4. Read multi-line service banners
5. Gather information beyond nmap scans

## Background

**Port scanning limitations:**
- nmap may not retrieve complete banners
- Some services show full information only after connection
- Welcome messages and MOTD require actual protocol handshake
- Interactive sessions reveal more than passive scans

**Why direct connection matters:**
- Complete multi-line banners
- Custom welcome messages from administrators
- Service-specific configuration details
- Information not visible in quick scans

## Step-by-Step Solution

### Step 1: Port Scan (Shows Limitations)

First, try scanning with nmap:

```bash
nmap -p 21 -sV 10.10.{user_id}.10
```

**Output:**
```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     ProFTPD 1.3.5
```

**What's missing:**
- This shows FTP is running
- But it doesn't show the complete welcome banner
- Custom messages and details are not captured
- This is where direct connection is needed

### Step 2: Connect with FTP Client

Use the FTP client to connect directly:

```bash
ftp 10.10.{user_id}.10
```

**Expected interaction:**
```
Connected to 10.10.{user_id}.10.
220-======================================
220-Welcome to the TechStart file transfer service
220-This server is for authorized use only
220-
220-Server: ProFTPD 1.3.5
220-Flag: OCR{ftp_1nt3r4ct}
220-
220-For support contact: it@techstart.local
220-======================================
220 ProFTPD 1.3.5 Server ready.
Name (10.10.{user_id}.10:user):
```

### Step 3: Read the Complete Banner

**Banner structure:**
- Lines starting with `220-` are part of the multi-line welcome banner
- The final `220` (without dash) ends the banner
- Custom information appears between the header and footer

**Key information extracted:**
1. Service name: "TechStart file transfer service"
2. Server type: ProFTPD 1.3.5
3. **Flag**: `OCR{ftp_1nt3r4ct}`
4. Contact: it@techstart.local

### Step 4: Disconnect

At the `Name` prompt, you can disconnect:

```
Name (10.10.{user_id}.10:user): quit
221 Goodbye.
```

Or press `Ctrl+C` to exit.

## Alternative Methods

### Method 1: Using Netcat

```bash
nc 10.10.{user_id}.10 21
```

This shows the raw FTP banner immediately.

### Method 2: Using Telnet

```bash
telnet 10.10.{user_id}.10 21
```

Similar to netcat, displays the welcome banner.

## Key Takeaways

### Port Scanning vs. Direct Connection

**nmap scan:**
- Fast, automated
- Captures basic service information
- May miss multi-line banners
- Good for initial reconnaissance

**Direct connection:**
- Shows complete welcome messages
- Reveals custom configurations
- Captures all banner lines
- Essential for thorough enumeration

### Professional Enumeration Workflow

1. **Port scan** - Identify running services
2. **Direct connection** - Gather complete information
3. **Service interaction** - Test commands and behavior
4. **Documentation** - Record all findings

### FTP Banner Information

FTP banners often reveal:
- Server software and version
- Operating system hints
- Organization name
- Administrator contact information
- Custom security messages
- Service purpose and policies

## Common Mistakes

### Mistake 1: Only Using Nmap

**Wrong approach:**
```bash
nmap -p 21 -sV 10.10.{user_id}.10
# Student stops here, misses the flag
```

**Right approach:**
```bash
nmap -p 21 -sV 10.10.{user_id}.10  # Initial scan
ftp 10.10.{user_id}.10              # Direct connection for complete info
```

### Mistake 2: Not Reading the Full Banner

**Problem:**
- Student connects with FTP
- Sees first line and disconnects
- Misses the flag in line 6

**Solution:**
- Wait for ALL `220` lines to display
- Read the complete banner before responding
- Don't rush to the `Name` prompt

### Mistake 3: Trying to Login

**Unnecessary:**
```
Name (10.10.{user_id}.10:user): anonymous
```

The flag is in the **welcome banner** before login, so you don't need to authenticate.

## Real-World Application

### Why This Matters

In real penetration tests:
- Custom banners often reveal organization details
- Welcome messages may expose sensitive information
- Version strings help identify vulnerabilities
- Contact information aids social engineering research

### Banner Grabbing Techniques

**Different services, different tools:**
- **FTP (21)**: `ftp`, `nc`, `telnet`
- **SSH (22)**: `ssh`, `nc`
- **SMTP (25)**: `nc`, `telnet`
- **HTTP (80)**: `curl -I`, `nc`
- **MySQL (3306)**: `mysql client`

### Defensive Recommendations

**Banner customization:**
```
# Bad - reveals everything
220 ProFTPD 1.3.5 Server (TechStart Production)

# Better - minimal information
220 FTP Service Ready
```

**Security through obscurity:**
- Remove version numbers
- Use generic messages
- Don't reveal OS or organization
- Limit information disclosure

## Advanced Techniques

### Testing Anonymous Access

After viewing the banner:

```
Name (10.10.{user_id}.10:user): anonymous
Password: [email address]
ftp> ls
ftp> quit
```

### FTP Commands for Enumeration

```
ftp> help        # List available commands
ftp> syst        # Display system type
ftp> stat        # Server status
ftp> ls          # List files (if authenticated)
```

## Conclusion

You've successfully:
- ✅ Understood port scanning limitations
- ✅ Connected directly to FTP service
- ✅ Read complete multi-line banner
- ✅ Gathered information beyond nmap
- ✅ Captured the flag from service interaction

**Critical lesson:** Port scanning provides initial reconnaissance, but complete enumeration requires direct service interaction. Always connect to services using appropriate clients to gather full information.

## References

- [ProFTPD Documentation](http://www.proftpd.org/docs/)
- [FTP Protocol (RFC 959)](https://tools.ietf.org/html/rfc959)
- [Banner Grabbing Techniques](https://owasp.org/www-community/Banner_Grabbing)
