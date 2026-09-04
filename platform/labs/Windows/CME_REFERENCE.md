# CrackMapExec (CME) Educational Reference

## What is CrackMapExec?

CrackMapExec (a.k.a CME) is a post-exploitation tool that helps assess the security of large networks composed of Windows workstations and servers. It's often described as a "Swiss army knife" for penetration testing Windows networks.

## Why Use CrackMapExec?

### The Problem It Solves

Imagine these scenarios:

1. **Large Network Assessment**: You're working on an internal security assessment of over 1,000 Windows workstations and servers. You have a single set of credentials. How do you quickly test whether these credentials work as local administrator on one or more machines?

2. **Credential Validation**: You have one target and several sets of credentials, but need to know if they're still valid. How do you test them quickly across multiple services?

3. **Post-Exploitation Automation**: You obtained local administrator credentials and want to dump the SAM file on each compromised workstation quickly. Do you manually connect to each one, or automate the process?

### The CME Solution

CrackMapExec automates these tasks by:
- Testing credentials across multiple protocols (SMB, RDP, WinRM, MSSQL, SSH, LDAP)
- Working with multiple targets simultaneously
- Gathering discovered credentials into a database for later use
- Providing intuitive, color-coded output
- Supporting socks proxy for pivoting
- Running on both Linux and Windows

## CME vs Manual Tools

### Manual Approach (What You've Learned)

In previous labs, you've used individual tools:
```bash
# Test SMB credentials
smbclient //target/share -U admin -p password123

# Test RDP credentials  
xfreerdp /v:target /u:admin /p:password123

# Test WinRM credentials
evil-winrm -i target -u admin -p password123
```

**Advantages of Manual Tools**:
- Full control over each step
- Better understanding of underlying protocols
- Easier to debug issues
- Good for learning fundamentals

**Disadvantages**:
- Time-consuming on large networks
- Repetitive tasks
- Hard to track credentials across services
- No centralized credential database

### CME Approach (Automation)

CME automates credential testing:
```bash
# Test credentials on SMB across entire network
crackmapexec smb <subnet> -u admin -p password123

# Test credentials on multiple protocols
crackmapexec smb target -u admin -p password123
crackmapexec rdp target -u admin -p password123
crackmapexec winrm target -u admin -p password123

# Use credential database
crackmapexec smb target --shares --sam
```

**Advantages of CME**:
- Fast credential testing across networks
- Multi-protocol support in one tool
- Credential database for tracking
- Post-exploitation automation
- Industry-standard tool

**Disadvantages**:
- Less visibility into individual steps
- Requires understanding of underlying concepts (which you now have!)
- Can be overwhelming without manual tool knowledge

## When to Use CME

### Use CME When:
- Testing credentials across multiple targets
- Working with large networks (10+ machines)
- Need to test credentials on multiple protocols quickly
- Want to automate post-exploitation tasks
- Need to track credentials in a database

### Use Manual Tools When:
- Learning a new protocol or technique
- Debugging connection issues
- Working with a single target
- Need fine-grained control
- Understanding the underlying protocol

## CME Architecture

CME heavily uses the **Impacket library** to work with network protocols and perform post-exploitation techniques. Impacket provides Python classes for working with network protocols like SMB, RDP, WinRM, and more.

## Installation

### On Kali Linux
```bash
# CME is pre-installed on Kali Linux
crackmapexec --version

# If not installed:
sudo apt update
sudo apt install crackmapexec
```

### Alternative: NetExec
As of 2023, some developers created NetExec as a fork/continuation:
```bash
# Install NetExec (CME v6+)
pipx install netexec
```

## Common CME Commands

### Basic Credential Testing
```bash
# Test SMB credentials
crackmapexec smb <target> -u <username> -p <password>

# Test RDP credentials
crackmapexec rdp <target> -u <username> -p <password>

# Test WinRM credentials
crackmapexec winrm <target> -u <username> -p <password>

# Test MSSQL credentials
crackmapexec mssql <target> -u <username> -p <password>
```

### Network-Wide Testing
```bash
# Test credentials across entire subnet
crackmapexec smb <subnet> -u admin -p password123

# Test with user list
crackmapexec smb <target> -u users.txt -p password123

# Test with password list
crackmapexec smb <target> -u admin -p passwords.txt
```

### Enumeration
```bash
# List SMB shares
crackmapexec smb <target> --shares

# Enumerate users
crackmapexec smb <target> --users

# Enumerate groups
crackmapexec smb <target> --groups
```

### Post-Exploitation
```bash
# Dump SAM file (requires admin)
crackmapexec smb <target> -u admin -p password123 --sam

# Execute command
crackmapexec smb <target> -u admin -p password123 -x "whoami"

# Upload file
crackmapexec smb <target> -u admin -p password123 --put-file local.txt remote.txt
```

### Credential Database
```bash
# View stored credentials
crackmapexec smb <target> --shares

# CME automatically stores working credentials in database
# Access via CME's database feature
```

## Understanding CME Output

CME uses color-coded output:
- **Green [+]**: Success (credentials work, command executed)
- **Red [-]**: Failure (credentials failed, error occurred)
- **Yellow [*]**: Information (enumeration results, etc.)

Example output:
```
SMB         <target_ip>     445    TARGET01         [+] admin:password123 (Pwn3d!)
RDP         <target_ip>     3389   TARGET01         [+] admin:password123
WINRM       <target_ip>     5985   TARGET01         [-] admin:password123
```

## CME Version Information

### CrackMapExec 5.4
- Last public version (June 2021)
- Available on GitHub
- Free and open source
- Used in this curriculum

### Porchetta Industries Version
- Updated version with latest features
- Requires $60 sponsorship for 6 months
- Private repository merged with public every 6 months
- Community contributions available immediately

### NetExec (CME v6+)
- Fork/continuation project (2023+)
- Repository: https://github.com/Pennyw0rth/NetExec
- Latest updates and features
- Can be used as alternative to CME 5.4

## Learning Path

1. **Manual Tools First** (Labs 8-15.4): Learn individual tools and protocols
2. **CME Introduction** (Lab 15.5): Understand automation and CME basics
3. **CME Application** (Labs 16.2-16.3): Use CME for comprehensive testing

## Real-World Application

CME is used by:
- Penetration testers for internal assessments
- Red teams for adversary simulation
- Blue teams for privilege assessment and misconfiguration detection
- Security researchers for network security testing

## Further Resources

- Official CME Wiki: https://wiki.porchetta.industries/
- NetExec Repository: https://github.com/Pennyw0rth/NetExec
- Impacket Library: https://github.com/fortra/impacket

## Key Takeaways

1. **CME automates** what you've learned to do manually
2. **Understanding manual tools** makes CME more effective
3. **Use CME for efficiency** on large networks
4. **Use manual tools** for learning and debugging
5. **CME is industry-standard** for Windows network assessments

