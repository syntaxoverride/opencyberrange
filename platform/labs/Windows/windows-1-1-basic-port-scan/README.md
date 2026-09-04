# Lab 1.1: Basic Windows Port Scan

## Learning Objectives

- Perform basic nmap port scan on target
- Identify SMB service on port 445
- Understand basic nmap syntax for Windows scanning
- Capture the flag

## Solution Walkthrough

### Step 1: Obtain Target IP Address

Before scanning, you need to know the target IP address.

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

   **What this means:**
   - If you get replies, the target is online and reachable
   - If you get "Destination Host Unreachable" or timeouts, check the IP address

### Step 2: Perform Basic Port Scan

Use nmap to scan the target and discover open ports and services.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   # Should output: /usr/bin/nmap or similar
   
   nmap --version
   # Should show nmap version information
   ```

2. **Run a basic nmap scan:**
   ```bash
   nmap <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP

   **What this command does:**
   - Scans the top 1000 most common ports
   - Performs service detection on open ports
   - Attempts OS detection
   - Takes approximately 1-2 minutes

3. **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   Not shown: 999 closed ports
   PORT    STATE SERVICE
   445/tcp open  microsoft-ds
   
   Nmap done: 1 IP address (1 host up) scanned in 45.23 seconds
   ```

   **Output explanation:**
   - `Host is up`: Target is online and responding
   - `PORT 445/tcp open microsoft-ds`: Port 445 is open, running Microsoft Directory Services (SMB)
   - `Not shown: 999 closed ports`: 999 other ports were scanned but are closed

4. **Alternative: Scan with more verbose output:**
   ```bash
   nmap -v <target_ip>
   ```
   
   The `-v` flag provides more detailed information during the scan.

### Step 3: Identify SMB Port

Analyze the scan results to identify the SMB service.

**Detailed Steps:**

1. **Look for port 445 in the results:**
   - Port 445 is the standard port for SMB (Server Message Block)
   - SMB is used by Windows for file sharing and network services
   - The service name may appear as `microsoft-ds` or `smb`

2. **Verify SMB service:**
   ```bash
   nmap -p 445 -sV <target_ip>
   ```
   
   The `-sV` flag performs version detection to get more details about the service.

   **Expected output:**
   ```
   PORT    STATE SERVICE       VERSION
   445/tcp open  microsoft-ds  Samba smbd 4.x
   ```

3. **Key indicators of SMB:**
   - Port 445 is open
   - Service name: `microsoft-ds`, `smb`, or `samba`
   - Protocol: TCP

**What is SMB?**
- Server Message Block (SMB) is a network protocol for file sharing
- Used by Windows for network file and printer sharing
- Port 445 is the standard SMB port (older versions used port 139)
- Can be used to access shared folders and files

### Step 4: Access the SMB Share

Connect to the SMB service to access the public share containing the flag.

**Detailed Steps:**

1. **Verify smbclient is installed:**
   ```bash
   which smbclient
   # Should output: /usr/bin/smbclient or similar
   ```

2. **Connect to the public share:**
   ```bash
   smbclient //<target_ip>/public
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `smbclient`: SMB client tool
   - `//<target_ip>/public`: SMB share path
     - `//` indicates SMB/CIFS protocol
     - `<target_ip>` is the target server
     - `/public` is the share name

3. **Expected connection prompt:**
   ```
   Enter WORKGROUP\root's password:
   ```
   
   **For anonymous/public access:**
   - Press `Enter` without typing a password
   - Or use the `-N` flag to skip password prompt

4. **Alternative: Connect with anonymous access flag:**
   ```bash
   smbclient //<target_ip>/public -N
   ```
   
   The `-N` flag means "no password" and is used for anonymous access.

5. **Expected successful connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```
   
   You should see the SMB prompt `smb: \>`, indicating you're connected to the share.

**Troubleshooting:**
- If you get "Connection refused", verify the IP address and that port 445 is open
- If you get "NT_STATUS_ACCESS_DENIED", the share may require credentials
- If you get "NT_STATUS_BAD_NETWORK_NAME", check the share name (should be `public`)
- Try with `-N` flag if password prompt appears: `smbclient //<target_ip>/public -N`

### Step 5: List Files in the Share

Once connected, explore the share to find the flag file.

**Detailed Steps:**

1. **List files and directories:**
   ```bash
   ls
   ```
   
   Type `ls` at the SMB prompt (`smb: \>`).

2. **Expected output:**
   ```
     .                                   D        0  Mon Jan 15 10:00:00 2024
     ..                                  D        0  Mon Jan 15 10:00:00 2024
     flag.txt                            A       45  Mon Jan 15 10:00:00 2024
   
                   524288 blocks of size 1024. 524288 blocks available
   ```

   **Output explanation:**
   - `.` and `..` are current and parent directories
   - `flag.txt` is the file we need (A = Archive/File, 45 = size in bytes)
   - The last line shows disk space information

3. **Get help with available commands:**
   ```bash
   help
   ```
   
   This shows all available SMB client commands.

4. **Common SMB client commands:**
   - `ls` or `dir`: List files
   - `cd <directory>`: Change directory
   - `get <file>`: Download a file
   - `put <file>`: Upload a file
   - `exit` or `quit`: Exit SMB client

### Step 6: Retrieve the Flag

Download the flag file from the SMB share.

**Detailed Steps:**

1. **Download the flag file:**
   ```bash
   get flag.txt
   ```
   
   Type `get flag.txt` at the SMB prompt.

2. **Expected output:**
   ```
   getting file \flag.txt of size 45 as flag.txt (0.3 KiloBytes/sec) (average 0.3 KB/s)
   ```

3. **Exit SMB client:**
   ```bash
   exit
   ```
   
   Or type `quit` to disconnect.

4. **Verify the file was downloaded:**
   ```bash
   ls -la flag.txt
   cat flag.txt
   ```

5. **Expected flag content:**
   ```
   OCR{b4s1c_p0rt_sc4n}
   ```

**Alternative: Download to specific location:**
```bash
get flag.txt /tmp/flag.txt
```

**Troubleshooting:**
- If `get` command fails, verify the filename is correct (case-sensitive)
- Check file permissions if download fails
- Use `pwd` to see current directory in SMB share
- Use `cd` to navigate if flag is in a subdirectory

### Step 7: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{b4s1c_p0rt_sc4n}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Successfully pinged target to verify connectivity
- ✅ Ran nmap scan and identified port 445 (SMB)
- ✅ Connected to SMB share using smbclient
- ✅ Listed files in the share
- ✅ Downloaded flag.txt from the public share
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Not scanning all ports (using default top 1000 ports)
- Confusing SMB port 445 with other ports
- Not recognizing SMB service in nmap output

## Hints for Struggling Students

1. Use `nmap <target_ip>` for a basic scan
2. Look for port 445 in the results
3. SMB is the Server Message Block protocol used by Windows
4. The flag is in a public share accessible without credentials

