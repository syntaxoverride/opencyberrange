# Lab 5.6: WinRM File Retrieval
## Learning Objectives
- Retrieve flag file via WinRM
- Understand file operations
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

### Step 3: Find Flag

Search the system to locate the flag file.

**Detailed Steps:**

1. **Search entire system for flag.txt:**
   ```bash
   find / -name flag.txt 2>/dev/null
   ```

   **Command breakdown:**
   - `find /`: Search from root directory
   - `-name flag.txt`: Look for files named flag.txt
   - `2>/dev/null`: Suppress error messages (permission denied, etc.)

2. **Expected output:**
   ```
   /tmp/flag.txt
   ```

3. **Alternative: Search in home directory:**
   ```bash
   find ~ -name flag.txt 2>/dev/null
   ```

4. **Alternative: Search in common locations:**
   ```bash
   ls -la /tmp/flag.txt
   ls -la ~/flag.txt
   ls -la /home/admin/flag.txt
   ```

5. **Alternative: Search for flag content:**
   ```bash
   grep -r "OCR{" /tmp 2>/dev/null
   ```

### Step 4: Retrieve Flag

Access and view the flag file from its location.

**Detailed Steps:**

1. **View flag from /tmp directory:**
   ```bash
   cat /tmp/flag.txt
   ```

2. **Expected flag content:**
   ```
   OCR{w1nrm_f1l3_r3tr13v3}
   ```

3. **Alternative: Check file permissions:**
   ```bash
   ls -la /tmp/flag.txt
   ```

   **Expected output:**
   ```
   -rw-r--r-- 1 admin admin 45 Jan 15 10:00 /tmp/flag.txt
   ```

4. **Alternative: Copy flag to home directory:**
   ```bash
   cp /tmp/flag.txt ~/flag_copy.txt
   cat ~/flag_copy.txt
   ```

5. **Copy flag:**
   - Select flag text
   - Copy to clipboard (Ctrl+Shift+C in terminal)

6. **Exit SSH session:**
   ```bash
   exit
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{w1nrm_f1l3_r3tr13v3}
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
- ✅ Used find command to locate flag.txt in /tmp directory
- ✅ Retrieved flag content using cat command
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- WinRM allows file retrieval from remote systems
- find command helps locate files across the system
- Understanding file system structure helps locate flags
- /tmp directory is a common location for temporary files
- File operations are essential for post-exploitation
## Hints
1. Connect with admin:password123
2. Flag in /tmp directory
3. Use find command to locate