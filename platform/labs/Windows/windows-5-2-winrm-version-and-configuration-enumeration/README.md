# Lab 5.2: WinRM Version and Configuration Enumeration
## Learning Objectives
- Enumerate WinRM version and authentication methods
- Understand WinRM-specific enumeration
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

### Step 2: Version Detection

Use nmap with version detection to identify WinRM version and configuration.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Run version detection scan:**
   ```bash
   nmap -sV -p 5985,5986 <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `nmap -sV -p 5985,5986 <target_ip>`)

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-sV`: Version detection (probes service to determine version)
   - `-p 5985,5986`: Scan WinRM ports (5985 HTTP, 5986 HTTPS)
   - `<target_ip>`: Target IP address

3. **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT     STATE SERVICE       VERSION
   5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
   5986/tcp open  ssl/http      Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
   
   Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
   Nmap done: 1 IP address (1 host up) scanned in 6.45 seconds
   ```

4. **Enhanced scan with scripts:**
   ```bash
   nmap -sV -sC -p 5985,5986 <target_ip>
   ```

### Step 3: Analyze Configuration

Review the version detection output to understand WinRM configuration.

**Detailed Steps:**

1. **Look for version information:**
   - **Service**: `http` or `ssl/http` (WinRM over HTTP/HTTPS)
   - **Version**: `Microsoft HTTPAPI httpd 2.0`
   - **Ports**: 5985 (HTTP) and/or 5986 (HTTPS)

2. **Check authentication methods:**
   - WinRM supports various authentication methods
   - Common methods: Basic, Negotiate, Kerberos, Certificate
   - Version detection may reveal supported methods

3. **Key configuration details:**
   - **Port 5985**: WinRM over HTTP (unencrypted)
   - **Port 5986**: WinRM over HTTPS (encrypted)
   - **Service**: Microsoft HTTPAPI indicates WinRM
   - **OS**: Windows (indicated by Microsoft service)

4. **Additional enumeration:**
   ```bash
   # Check WinRM configuration (if accessible)
   curl -k https://<target_ip>:5986/wsman
   ```

### Step 4: Access Flag

Connect via SSH (WinRM alternative in this lab) to retrieve the flag.

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

3. **Enter password when prompted:**
   ```
   admin@<target_ip>'s password:
   ```
   
   Type: `password123` (password will not be visible as you type)

4. **Expected successful connection:**
   ```
   Welcome to Ubuntu 20.04.5 LTS
   ...
   admin@target:~$
   ```

5. **View flag:**
   ```bash
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{w1nrm_3num}
   ```

6. **Alternative locations to check:**
   ```bash
   cat ~/flag.txt
   cat /home/admin/flag.txt
   cat /tmp/flag.txt
   find ~ -name "flag.txt" 2>/dev/null
   ```

7. **Exit SSH session:**
   ```bash
   exit
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{w1nrm_3num}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Ran nmap version detection on WinRM ports (5985, 5986)
- ✅ Identified WinRM service version and configuration
- ✅ Analyzed authentication methods and capabilities
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
1. Use nmap -sV for version
2. Check authentication methods
3. Connect with admin:password123