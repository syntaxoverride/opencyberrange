# Lab 5.1: WinRM Service Detection
## Learning Objectives
- Identify WinRM service on target
- Understand WinRM enumeration
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before scanning.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

   **Expected output:**
   ```
   PING <target_ip> (<target_ip>) 56(84) bytes of data.
   64 bytes from <target_ip>: icmp_seq=1 ttl=64 time=0.123 ms
   64 bytes from <target_ip>: icmp_seq=2 ttl=64 time=0.098 ms
   64 bytes from <target_ip>: icmp_seq=3 ttl=64 time=0.105 ms
   ```

### Step 2: Scan for WinRM Service

Use nmap to scan for WinRM (Windows Remote Management) on its standard ports.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Scan for WinRM ports:**
   ```bash
   nmap -p 5985,5986 <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `nmap -p 5985,5986 <target_ip>`)

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-p 5985,5986`: Scan ports 5985 (HTTP) and 5986 (HTTPS) - WinRM ports
   - `<target_ip>`: Target IP address

   **WinRM Ports:**
   - **Port 5985**: WinRM over HTTP
   - **Port 5986**: WinRM over HTTPS (secure)

3. **Expected output if WinRM is running:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT     STATE SERVICE
   5985/tcp open  http
   5986/tcp open  ssl/http
   
   Nmap done: 1 IP address (1 host up) scanned in 0.45 seconds
   ```

4. **Enhanced scan with version detection:**
   ```bash
   nmap -p 5985,5986 -sV <target_ip>
   ```

   **Expected output with version:**
   ```
   PORT     STATE SERVICE       VERSION
   5985/tcp open  http          SimpleHTTPServer 0.6 (Python 3.10.12)
   5986/tcp open  http          SimpleHTTPServer 0.6 (Python 3.10.12)
   ```

   In this lab the WinRM endpoint is fingerprinted as a Python HTTP server, so `nmap -sV` reports `SimpleHTTPServer 0.6 (Python 3.10.12)` instead of "Microsoft HTTPAPI httpd 2.0". On a real Windows host nmap prints the Microsoft string directly. Confirm the WinRM banner here with curl:
   ```bash
   curl -I http://<target_ip>:5985
   ```
   The response includes `Server: Microsoft-HTTPAPI/2.0`, which is the reliable WinRM indicator on this target.

5. **Alternative: Scan with service detection:**
   ```bash
   nmap -p 5985,5986 -sC -sV <target_ip>
   ```

### Step 3: Verify WinRM Service

Confirm that the detected service is WinRM and understand what it is.

**Detailed Steps:**

1. **What is WinRM?**
   - **WinRM** = Windows Remote Management
   - Port **5985**: WinRM over HTTP (unencrypted)
   - Port **5986**: WinRM over HTTPS (encrypted)
   - Used for remote management and PowerShell execution on Windows
   - Similar to SSH but for Windows systems

2. **Key indicators of WinRM:**
   - Port 5985 or 5986 is open
   - Service name: `http` or `ssl/http` (can be misleading)
   - `Server: Microsoft-HTTPAPI/2.0` in the HTTP response headers (confirm with `curl -I`)
   - Used for remote Windows management

3. **Verify with netcat (alternative):**
   ```bash
   nc -zv <target_ip> 5985
   nc -zv <target_ip> 5986
   ```

   **Expected output:**
   ```
   Connection to <target_ip> 5985 port [tcp/http] succeeded!
   Connection to <target_ip> 5986 port [tcp/ssl/http] succeeded!
   ```

### Step 4: Access Flag via SSH (WinRM Alternative)

**Note:** This lab uses SSH as a WinRM alternative for educational purposes. In real scenarios, you would use tools like `evil-winrm` or `winrm-cli`.

**Detailed Steps:**

1. **Verify SSH client is available:**
   ```bash
   which ssh
   ```

2. **Connect via SSH:**
   ```bash
   ssh admin@<target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP.

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
   
   Type: `password123` (password will not be visible as you type)

5. **Expected successful connection:**
   ```
   Welcome to Ubuntu 20.04.5 LTS
   ...
   admin@target:~$
   ```

   You should see the command prompt, indicating you're logged in.

**Troubleshooting SSH connection:**
- **"Connection refused"**: Verify IP and that SSH service is running
- **"Permission denied"**: Check username (admin) and password (password123)
- **"Host key verification failed"**: Remove old key: `ssh-keygen -R <target_ip>`

### Step 5: Locate and Retrieve Flag

Once connected via SSH, navigate to the flag file location.

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
   find ~ -name "flag.txt" 2>/dev/null
   ```

   Or check common locations:
   ```bash
   cat ~/flag.txt
   cat /home/admin/flag.txt
   cat /tmp/flag.txt
   ```

4. **Expected flag location:**
   ```bash
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{w1nrm_d3t3ct}
   ```

5. **Alternative: Search for flag:**
   ```bash
   grep -r "OCR{" ~ 2>/dev/null
   ```

### Step 6: Copy Flag and Exit

Extract the flag and disconnect from the SSH session.

**Detailed Steps:**

1. **View flag content:**
   ```bash
   cat flag.txt
   ```

2. **Copy the flag:**
   - Select the flag text: `OCR{w1nrm_d3t3ct}`
   - Copy to clipboard (Ctrl+Shift+C in terminal)

3. **Exit SSH session:**
   ```bash
   exit
   ```

   Or press `Ctrl+D`

4. **Verify flag format:**
   - Flag should be in your clipboard or notes
   - Format: `OCR{...}`

### Step 7: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{w1nrm_d3t3ct}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Scanned for WinRM ports (5985, 5986) using nmap
- ✅ Identified WinRM service on port 5985 or 5986
- ✅ Successfully connected via SSH (WinRM alternative)
- ✅ Logged in with credentials (admin/password123)
- ✅ Located and viewed flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Note on Real WinRM Tools:**
In real-world scenarios, you would use:
- `evil-winrm`: `evil-winrm -i <target_ip> -u admin -p password123`
- `winrm-cli`: `winrm-cli -hostname <target_ip> -username admin -password password123`
- PowerShell: `Enter-PSSession -ComputerName <target_ip> -Credential admin`
## Hints
1. WinRM typically on ports 5985/5986
2. Use nmap to detect
3. Flag accessible after connection