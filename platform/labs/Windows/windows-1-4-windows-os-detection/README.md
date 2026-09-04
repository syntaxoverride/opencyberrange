# Lab 1.4: Windows OS Detection

## Learning Objectives

- Use nmap OS detection (-O) to identify operating system
- Use HTTP and web services to retrieve information from a target
- Interpret OS detection and service enumeration results
- Understand OS fingerprinting concepts
- Capture the flag (served via HTTP and embedded in SMB server string)

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

### Step 2: Perform OS Detection Scan

Use nmap with OS detection to identify the operating system running on the target.

**Detailed Steps:**

1. **OS detection requires root privileges:**
   ```bash
   sudo nmap -O <target_ip>
   ```
   
   **Command breakdown:**
   - `sudo`: Required for OS detection (needs raw socket access)
   - `nmap`: Network mapper tool
   - `-O`: Enable OS detection (operating system fingerprinting)

2. **Expected output:**
   ```
   PORT    STATE SERVICE
   139/tcp open  netbios-ssn
   445/tcp open  microsoft-ds
   
   OS details: Linux 4.15 - 5.19 (running Samba to appear as Windows)
   ```

3. **Note:** The target runs Linux with Samba configured to appear as a Windows server. This is common in lab environments.

### Step 3: Retrieve the Flag

The flag is served by a web server running on the target. Use curl or a browser to retrieve it directly.

**Detailed Steps:**

1. **Use curl to retrieve the flag via HTTP:**
   ```bash
   curl http://<target_ip>/flag.txt
   ```

   **Expected output:**
   ```
   OCR{0s_d3t3ct10n}
   ```

2. **Alternative discovery method: SMB server string enumeration.**
   The flag is also embedded in the Samba server string. Students who enumerate SMB shares will find it in the IPC$ share comment:
   ```bash
   smbclient -L //<target_ip> -N
   ```

   **Expected output:**
   ```
   Sharename       Type      Comment
   ---------       ----      -------
   IPC$            IPC       IPC Service (Windows Server 2019 - Flag: OCR{0s_d3t3ct10n})
   ```

3. **Alternative: Use enum4linux for detailed enumeration:**
   ```bash
   enum4linux -a <target_ip>
   ```

   Look for the "Server Comment" or "OS information" in the output.

### Step 4: Verify Flag Format

**Flag format:**
```
OCR{0s_d3t3ct10n}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Ran nmap with OS detection using `sudo nmap -O`
- ✅ Retrieved the flag via HTTP using `curl http://<target_ip>/flag.txt`
- ✅ Found the flag served by the web server (also visible in SMB server string)
- ✅ Understood how OS detection and service enumeration work together
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Not using sudo for OS detection (requires root)
- Overlooking the HTTP service when focusing only on SMB
- Not checking common file paths like `/flag.txt` on web servers
- Not reading the server comment/description carefully during SMB enumeration

## Hints for Struggling Students

1. Use `sudo nmap -O` for OS detection
2. The flag is served via HTTP - use `curl http://<ip>/flag.txt`
3. Check for common web-hosted files like `flag.txt` on any HTTP service
4. The flag can also be found in the SMB server string if you enumerate shares
