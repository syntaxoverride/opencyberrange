# Lab 4.2: RDP Version Enumeration

## Learning Objectives
- Identify RDP version and capabilities
- Understand version detection
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

Use nmap with version detection to identify the RDP version and capabilities.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Run version detection scan:**
   ```bash
   nmap -sV -p 3389 <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `nmap -sV -p 3389 <target_ip>`)

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-sV`: Version detection (probes service to determine version)
   - `-p 3389`: Scan port 3389 (RDP default port)
   - `<target_ip>`: Target IP address

3. **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT     STATE SERVICE       VERSION
   3389/tcp open  ms-wbt-server xrdp
   
   
   Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
   Nmap done: 1 IP address (1 host up) scanned in 6.45 seconds
   ```

4. **Enhanced scan with more details:**
   ```bash
   nmap -sV -sC -p 3389 <target_ip>
   ```
   
   The `-sC` flag runs default scripts for additional information.

### Step 3: Analyze Version

Carefully review the version detection output to understand RDP capabilities.

**Detailed Steps:**

1. **Look for RDP version information:**
   - **Service name**: `ms-wbt-server` (Microsoft Windows Based Terminal Server)
   - **Version**: May show specific RDP version or Windows version
   - **OS information**: Windows operating system details
   - **CPE**: Common Platform Enumeration identifier

2. **Key information from output:**
   ```
   SERVICE       VERSION
   ms-wbt-server xrdp
   OS: Linux
   
   ```

3. **What this tells us:**
   - RDP service is running (xrdp)
   - Operating system is Linux (Ubuntu 22.04)
   - Can identify Linux distribution from CPE or OS details
   - Helps select appropriate RDP client and connection parameters

4. **Additional version details (if available):**
   - RDP protocol version (RDP 8.0, 10.0, etc.)
   - Security layer information
   - Encryption capabilities
   - Authentication methods supported

### Step 4: Access Flag

Connect via RDP using the provided credentials to access the flag.

**Detailed Steps:**

1. **Verify RDP client is available:**
   ```bash
   which xfreerdp
   # Or
   which rdesktop
   ```

2. **Connect via RDP:**
   ```bash
   xfreerdp /v:<target_ip> /u:rdpuser /p:password123
   ```
   
   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `xfreerdp`: FreeRDP client for RDP connections
   - `/v:<target_ip>`: Target IP address
   - `/u:rdpuser`: Username for authentication
   - `/p:password123`: Password for authentication

3. **Expected connection:**
   - RDP client window will open
   - You'll see the Linux desktop (xfce4)
   - You're logged in as rdpuser

4. **Alternative: Connect with rdesktop:**
   ```bash
   rdesktop <target_ip> -u rdpuser -p password123
   ```

5. **Navigate to flag location:**
   - Open File Manager or terminal
   - Navigate to: `/home/rdpuser/flag.txt` or `/home/rdpuser/flag.txt`
   - Or use terminal: `cat /home\Users\rdpuser\flag.txt`

6. **Expected flag content:**
   ```
   OCR{rdp_v3rs10n}
   ```

**Troubleshooting:**
- If connection fails, verify credentials: `rdpuser` / `password123`
- Try with certificate ignore: `xfreerdp /v:<target_ip> /u:rdpuser /p:password123 /cert:ignore`
- Check if RDP service is actually running on port 3389

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{rdp_v3rs10n}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Ran nmap version detection on port 3389
- ✅ Identified RDP service version and OS information
- ✅ Analyzed version detection output
- ✅ Successfully connected via RDP using xfreerdp
- ✅ Logged in with credentials (rdpuser/password123)
- ✅ Located and viewed flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes
- Not using -sV flag
- Not reading version output

## Hints
1. Use `nmap -sV -p 3389`
2. Version appears in SERVICE column
3. Connect with xfreerdp