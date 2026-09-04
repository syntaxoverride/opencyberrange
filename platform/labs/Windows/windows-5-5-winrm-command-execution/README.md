# Lab 5.5: WinRM Command Execution
## Learning Objectives
- Execute commands via WinRM session
- Understand command execution
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

3. **Verify WinRM/SSH service is running:**
   ```bash
   nmap -p 5985,22 <target_ip>
   ```

### Step 2: Connect

Connect via SSH (WinRM alternative in this lab) using provided credentials.

**Detailed Steps:**

1. **Connect via SSH:**
   ```bash
   ssh admin@<target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `ssh admin@<target_ip>`)

2. **Enter password when prompted:**
   ```
   admin@<target_ip>'s password:
   ```
   
   Type: `password123` (password will not be visible as you type)

3. **Expected successful connection:**
   ```
   Welcome to Ubuntu 20.04.5 LTS
   ...
   admin@target:~$
   ```

### Step 3: Execute Commands

Execute various commands to explore the system and locate the flag.

**Detailed Steps:**

1. **Check current user:**
   ```bash
   whoami
   ```

   **Expected output:**
   ```
   admin
   ```

2. **List files in current directory:**
   ```bash
   ls
   ```

   **Expected output:**
   ```
   flag.txt  documents  scripts
   ```

3. **Check current directory:**
   ```bash
   pwd
   ```

   **Expected output:**
   ```
   /home/admin
   ```

4. **View flag file:**
   ```bash
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{w1nrm_cmd_3x3c}
   ```

5. **Additional useful commands:**
   ```bash
   # Check system information
   uname -a
   
   # Check network configuration
   ip addr
   
   # List running processes
   ps aux
   
   # Check file permissions
   ls -la flag.txt
   ```

### Step 4: Retrieve Flag

Extract and copy the flag from the system.

**Detailed Steps:**

1. **View flag content:**
   ```bash
   cat flag.txt
   ```

2. **Expected flag content:**
   ```
   OCR{w1nrm_cmd_3x3c}
   ```

3. **Alternative: If flag is in different location:**
   ```bash
   find ~ -name "flag.txt" 2>/dev/null
   cat ~/flag.txt
   cat /home/admin/flag.txt
   ```

4. **Copy flag:**
   - Select flag text
   - Copy to clipboard (Ctrl+Shift+C in terminal)

5. **Exit SSH session:**
   ```bash
   exit
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{w1nrm_cmd_3x3c}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and WinRM/SSH service accessibility
- ✅ Successfully connected via SSH (WinRM alternative)
- ✅ Logged in with credentials (admin/password123)
- ✅ Executed commands to explore system (whoami, ls, pwd)
- ✅ Located flag.txt in home directory
- ✅ Retrieved and copied flag content
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- WinRM allows remote command execution on Windows
- Commands can be executed interactively in a session
- Understanding command execution is essential for post-exploitation
- Multiple commands help explore and understand the system
## Hints
1. Connect with admin:password123
2. Execute commands in session
3. Flag in home directory