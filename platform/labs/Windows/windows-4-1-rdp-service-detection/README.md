# Lab 4.1: RDP Service Detection

## Learning Objectives
- Identify RDP service on target
- Understand RDP enumeration
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

### Step 2: Scan for RDP Service

Use nmap to scan for the RDP service on the standard port 3389.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Scan for RDP port (3389):**
   ```bash
   nmap -p 3389 <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `nmap -p 3389 <target_ip>`)

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-p 3389`: Scan only port 3389 (RDP default port)
   - `<target_ip>`: Target IP address

3. **Expected output if RDP is running:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT     STATE SERVICE
   3389/tcp open  ms-wbt-server
   
   Nmap done: 1 IP address (1 host up) scanned in 0.45 seconds
   ```

   **Output explanation:**
   - `PORT 3389/tcp open`: Port 3389 is open and accepting connections
   - `ms-wbt-server`: Service name for RDP (Microsoft Windows Based Terminal Server)
   - `STATE open`: Port is open and service is responding

4. **Alternative: Scan with version detection:**
   ```bash
   nmap -p 3389 -sV <target_ip>
   ```
   
   The `-sV` flag performs version detection to get more details.

   **Expected output with version:**
   ```
   PORT     STATE SERVICE       VERSION
   3389/tcp open  ms-wbt-server Microsoft Terminal Services
   ```

5. **If port is closed or filtered:**
   ```
   PORT     STATE    SERVICE
   3389/tcp closed  ms-wbt-server
   ```
   
   Or:
   ```
   PORT     STATE    SERVICE
   3389/tcp filtered ms-wbt-server
   ```
   
   **Troubleshooting:**
   - `closed`: Port is not listening (service not running)
   - `filtered`: Port might be open but firewall is blocking
   - Verify target IP is correct
   - Check if lab environment is running

### Step 3: Verify RDP Service

Confirm that the detected service is actually RDP and gather additional information.

**Detailed Steps:**

1. **What is RDP?**
   - **RDP** = Remote Desktop Protocol
   - Port **3389** is the standard RDP port
   - Used for remote desktop connections to Windows systems
   - Service name: `ms-wbt-server` (Microsoft Windows Based Terminal Server)

2. **Additional verification scan:**
   ```bash
   nmap -p 3389 -sC -sV <target_ip>
   ```
   
   The `-sC` flag runs default scripts, `-sV` performs version detection.

3. **Check RDP with netcat (alternative):**
   ```bash
   nc -zv <target_ip> 3389
   ```

   **Expected output:**
   ```
   Connection to <target_ip> 3389 port [tcp/ms-wbt-server] succeeded!
   ```

4. **Key indicators of RDP:**
   - Port 3389 is open
   - Service name: `ms-wbt-server` or `rdp`
   - Protocol: TCP
   - Used for remote desktop access

### Step 4: Connect via RDP

Connect to the target using an RDP client to access the remote desktop.

**Detailed Steps:**

1. **Verify RDP client is available:**
   ```bash
   which xfreerdp
   # Or
   which rdesktop
   ```

2. **Connect using xfreerdp (recommended):**
   ```bash
   xfreerdp /v:<target_ip> /u:rdpuser /p:password123
   ```
   
   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `xfreerdp`: FreeRDP client for RDP connections
   - `/v:<target_ip>`: Target IP address
   - `/u:rdpuser`: Username for authentication
   - `/p:password`: Password for authentication

3. **Alternative: Connect with rdesktop:**
   ```bash
   rdesktop <target_ip> -u rdpuser -p password123
   ```

4. **Expected connection process:**
   - RDP client window will open
   - You'll see the Linux desktop (xfce4)/login screen
   - If credentials are correct, you'll be logged in

5. **If connection fails:**
   - **"Connection refused"**: Verify IP and port 3389
   - **"Authentication failed"**: Check username/password
   - **"Connection timeout"**: Firewall may be blocking
   - Try: `xfreerdp /v:<target_ip> /u:rdpuser /p:password123 /cert:ignore`

**Common RDP client options:**
- `/v:<ip>`: Target IP address
- `/u:<user>`: Username
- `/p:<pass>`: Password
- `/cert:ignore`: Ignore certificate errors
- `/size:1024x768`: Set window size
- `/bpp:24`: Color depth

### Step 5: Locate and Retrieve Flag

Once connected via RDP, navigate to the flag file location.

**Detailed Steps:**

1. **After successful RDP connection:**
   - You should see the Linux desktop (xfce4)
   - You're logged in as `rdpuser`

2. **Open File Manager:**
   - Click the File Manager icon in the taskbar
   - Or click the File Manager icon in the taskbar

3. **Navigate to flag location:**
   - The flag is located at: `/home/rdpuser/flag.txt`
   - Or in Windows path format: `/home/rdpuser/flag.txt`
   - Or: `/home/rdpuser/flag.txt`

4. **Alternative: Use Terminal:**
   - Right-click the desktop and select "Open Terminal Here"
   - Or open a terminal from the applications menu
   - Navigate to flag location:
     ```bash
     cd /home/rdpuser
     ls flag.txt
     cat flag.txt
     ```

5. **View flag content:**
   - Double-click `flag.txt` to open in a text editor
   - Or use terminal: `cat flag.txt`
   - Or use terminal: `cat flag.txt`

6. **Expected flag content:**
   ```
   OCR{rdp_d3t3ct}
   ```

**Alternative: Copy flag to clipboard:**
- Select flag text in text editor
- Press `Ctrl+C` to copy
- Paste into your notes

### Step 6: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{rdp_d3t3ct}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters
- ✅ Copied correctly from RDP session

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Scanned for port 3389 using nmap
- ✅ Identified RDP service (ms-wbt-server) on port 3389
- ✅ Successfully connected via RDP using xfreerdp or rdesktop
- ✅ Logged in with credentials (rdpuser/password123)
- ✅ Located flag.txt in /home/rdpuser/ or /home/rdpuser\
- ✅ Retrieved and copied flag content
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes
- Not scanning port 3389
- Not recognizing RDP service

## Hints
1. RDP runs on port 3389
2. Use nmap to detect service
3. Flag is accessible after RDP connection