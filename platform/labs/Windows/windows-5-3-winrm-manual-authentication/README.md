# Lab 5.3: WinRM Manual Authentication
## Learning Objectives
- Authenticate to WinRM with known credentials
- Understand WinRM authentication
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before connecting.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Verify WinRM service is running:**
   ```bash
   nmap -p 5985,5986 <target_ip>
   ```

### Step 2: Authenticate

Connect via SSH (WinRM alternative in this lab) using provided credentials.

**Detailed Steps:**

1. **Verify SSH client is available:**
   ```bash
   which ssh
   ```

2. **Connect via SSH:**
   ```bash
   ssh admin@<target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `ssh admin@<target_ip>`)

3. **Accept host key (first time only):**
   ```
   The authenticity of host '<target_ip> (<target_ip>)' can't be established.
   ECDSA key fingerprint is SHA256:...
   Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
   ```

4. **Enter password when prompted:**
   ```
   admin@<target_ip>'s password:
   ```
   
   Type: `password` (password will not be visible as you type)

5. **Expected successful connection:**
   ```
   Welcome to Ubuntu 20.04.5 LTS
   ...
   admin@target:~$
   ```

   **What this means:**
   - Authentication was successful
   - You're now logged in as admin
   - You have shell access to the system

**Troubleshooting:**
- **"Connection refused"**: Verify IP and that SSH service is running
- **"Permission denied"**: Check username (admin) and password (password)
- **"Host key verification failed"**: Remove old key: `ssh-keygen -R <target_ip>`

### Step 3: Retrieve Flag

Locate and view the flag file on the system.

**Detailed Steps:**

1. **Check current directory:**
   ```bash
   pwd
   ```

2. **List files in current directory:**
   ```bash
   ls -la
   ```

3. **Look for flag file:**
   ```bash
   cat flag.txt
   ```

4. **If flag is not in current directory, search for it:**
   ```bash
   find ~ -name "flag.txt" 2>/dev/null
   ```

5. **Check common locations:**
   ```bash
   cat ~/flag.txt
   cat /home/admin/flag.txt
   cat /tmp/flag.txt
   ```

6. **Expected flag content:**
   ```
   OCR{w1nrm_m4nu4l_4uth}
   ```

7. **Alternative: Search for flag content:**
   ```bash
   grep -r "OCR{" ~ 2>/dev/null
   ```

8. **Copy flag:**
   - Select the flag text
   - Copy to clipboard (Ctrl+Shift+C in terminal)

9. **Exit SSH session:**
   ```bash
   exit
   ```

### Step 4: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{w1nrm_m4nu4l_4uth}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and WinRM/SSH service accessibility
- ✅ Successfully connected via SSH (WinRM alternative)
- ✅ Logged in with credentials (admin/password)
- ✅ Located flag.txt in home directory or system
- ✅ Retrieved and copied flag content
- ✅ Verified flag format is correct: `OCR{...}`

**Note on Real WinRM Authentication:**
In real-world scenarios, you would use:
- `evil-winrm`: `evil-winrm -i <target_ip> -u admin -p password`
- `winrm-cli`: `winrm-cli -hostname <target_ip> -username admin -password password`
- PowerShell: `Enter-PSSession -ComputerName <target_ip> -Credential admin`
## Hints
1. Username: admin
2. Password: password
3. Use SSH as WinRM alternative