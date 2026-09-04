# Lab 1.3: Windows Service Version Detection

## Learning Objectives

- Use nmap version detection (-sV) to identify service versions
- Interpret version information from nmap output
- Understand importance of version detection in enumeration
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

### Step 2: Perform Version Detection Scan

Use nmap with version detection to identify the exact versions of services running on open ports.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Run nmap with version detection:**
   ```bash
   nmap -sV <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-sV`: Enable version detection (probes services to determine version)
   - `<target_ip>`: Target IP address

3. **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   Not shown: 999 closed ports
   PORT    STATE SERVICE       VERSION
   445/tcp open  microsoft-ds  Samba smbd 4.15.5
   
   Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
   Nmap done: 1 IP address (1 host up) scanned in 12.45 seconds
   ```

4. **Compare with scan without version detection:**
   ```bash
   nmap <target_ip>
   ```
   
   Without `-sV`, you only see service names, not versions.

### Step 3: Analyze Version Information

Carefully review the version information to understand what software is running.

**Detailed Steps:**

1. **Look for version strings in the output:**
   - **Samba version**: `Samba smbd 4.15.5` (SMB service)
   - **RDP version**: `Microsoft Terminal Services` (if RDP is present)
   - **HTTP server version**: `Apache httpd 2.4.54` (if HTTP is present)

2. **Example output analysis:**
   ```
   PORT    STATE SERVICE       VERSION
   445/tcp open  microsoft-ds  Samba smbd 4.15.5
   ```
   
   **What this tells us:**
   - Port 445 is open
   - Service: microsoft-ds (SMB)
   - **Version: Samba smbd 4.15.5**
   - This is important for vulnerability research

3. **Why version detection matters:**
   - Identifies specific software versions
   - Enables searching for known vulnerabilities
   - Helps select appropriate exploitation tools
   - Reveals outdated software that needs patching

4. **Enhanced scan with more details:**
   ```bash
   nmap -sV -sC <target_ip>
   ```
   
   The `-sC` flag runs default scripts for additional information.

### Step 4: Access the Flag

The flag is served via HTTP, accessible after identifying the service.

**Detailed Steps:**

1. **Retrieve the flag via HTTP:**
   ```bash
   curl http://<target_ip>/flag.txt
   ```

   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `curl`: Command-line tool for transferring data via URLs
   - `http://<target_ip>/flag.txt`: URL path to the flag file served by nginx

2. **Expected output:**
   ```
   OCR{v3rs10n_d3t3ct10n}
   ```

**Alternative: via SMB**

The flag can also be retrieved from the public SMB share.

1. **Connect to public SMB share:**
   ```bash
   smbclient //<target_ip>/public -N
   ```

   **Command breakdown:**
   - `smbclient`: SMB client tool
   - `//<target_ip>/public`: SMB share path
   - `-N`: No password flag (anonymous access)

2. **List and download the flag:**
   ```bash
   ls
   get flag.txt
   exit
   ```

3. **View the flag:**
   ```bash
   cat flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{v3rs10n_d3t3ct10n}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Ran nmap with version detection (`-sV` flag)
- ✅ Identified service versions (e.g., Samba smbd 4.15.5)
- ✅ Understood importance of version detection
- ✅ Successfully retrieved flag.txt via HTTP
- ✅ Retrieved the flag from the web server
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Forgetting to use -sV flag
- Not reading version information carefully
- Skipping version detection step

## Hints for Struggling Students

1. Use `nmap -sV` for version detection
2. Version information appears in the SERVICE column
3. Version detection helps identify vulnerable software
4. The flag is accessible via HTTP at `/flag.txt`

