# Lab 1.2: Multiple Port Discovery

## Learning Objectives

- Perform full port scan on Windows host
- Identify multiple open ports (SMB 445, RDP 3389, HTTP 80)
- Understand service identification in nmap output
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

### Step 2: Perform Full Port Scan

Scan all ports on the target to discover all open services.

**Detailed Steps:**

1. **Option 1: Scan all ports (comprehensive but slower):**
   ```bash
   nmap -p- <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-p-`: Scan all 65535 ports (from 1 to 65535)
   - `<target_ip>`: Target IP address

   **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   Not shown: 65532 closed ports
   PORT     STATE SERVICE
   80/tcp   open  http
   445/tcp  open  microsoft-ds
   3389/tcp open  ms-wbt-server
   
   Nmap done: 1 IP address (1 host up) scanned in 120.45 seconds
   ```

   **Note:** Full port scan can take 2-5 minutes depending on network speed.

2. **Option 2: Scan common ports (faster):**
   ```bash
   nmap -p 1-1000 <target_ip>
   ```
   
   This scans ports 1-1000, which covers most common services.

   **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   Not shown: 997 closed ports
   PORT     STATE SERVICE
   80/tcp   open  http
   445/tcp  open  microsoft-ds
   3389/tcp open  ms-wbt-server
   
   Nmap done: 1 IP address (1 host up) scanned in 15.23 seconds
   ```

3. **Option 3: Scan specific ports (fastest):**
   ```bash
   nmap -p 80,445,3389 <target_ip>
   ```
   
   This only scans the three ports we're looking for.

4. **Enhanced scan with service detection:**
   ```bash
   nmap -p- -sV <target_ip>
   ```
   
   The `-sV` flag performs version detection to get detailed service information.

   **Expected output with versions:**
   ```
   PORT     STATE SERVICE       VERSION
   80/tcp   open  http          Microsoft IIS httpd 10.0
   445/tcp  open  microsoft-ds  Samba smbd 4.x
   3389/tcp open  ms-wbt-server Microsoft Terminal Services
   ```

### Step 3: Identify Services

Analyze the scan results to identify all open services and their purposes.

**Detailed Steps:**

1. **Review the scan output:**
   - Look for ports with `STATE open`
   - Note the service names
   - Identify which services are running

2. **Expected services to find:**
   - **Port 80**: HTTP (web server)
     - Service name: `http`
     - Used for web browsing and web services
   - **Port 445**: SMB (Server Message Block)
     - Service name: `microsoft-ds`
     - Used for file sharing and network services
   - **Port 3389**: RDP (Remote Desktop Protocol)
     - Service name: `ms-wbt-server`
     - Used for remote desktop connections

3. **Document your findings:**
   ```
   Open Ports:
   - Port 80: HTTP (web server)
   - Port 445: SMB (file sharing)
   - Port 3389: RDP (remote desktop)
   ```

4. **Verify services are actually running:**
   ```bash
   # Test HTTP
   curl -I http://<target_ip>
   
   # Test SMB
   smbclient -L //<target_ip> -N
   
   # Test RDP
   nc -zv <target_ip> 3389
   ```

### Step 4: Access the Flag via HTTP (Easiest Method)

The flag is accessible through any of the three services. HTTP is typically the simplest.

**Detailed Steps:**

1. **Access the web server:**
   ```bash
   curl http://<target_ip>/
   ```

2. **Check for flag file:**
   ```bash
   curl http://<target_ip>/flag.txt
   ```

   **Expected output:**
   ```
   OCR{mult1pl3_p0rts}
   ```

3. **Alternative: Use browser:**
   - Open browser
   - Navigate to: `http://<target_ip>/flag.txt`
   - Copy the flag

**Troubleshooting:**
- If you get 404, try: `http://<target_ip>/flag`, `http://<target_ip>/FLAG.txt`
- Check for directory listing: `http://<target_ip>/`

### Step 5: Access the Flag via SMB (Alternative Method)

If HTTP doesn't work, try accessing via SMB.

**Detailed Steps:**

1. **List available SMB shares:**
   ```bash
   smbclient -L //<target_ip> -N
   ```

2. **Connect to public share:**
   ```bash
   smbclient //<target_ip>/public -N
   ```

3. **List files:**
   ```bash
   ls
   ```

4. **Download flag:**
   ```bash
   get flag.txt
   exit
   ```

5. **View flag:**
   ```bash
   cat flag.txt
   ```

### Step 6: Access the Flag via RDP (Alternative Method)

If other methods don't work, try RDP.

**Detailed Steps:**

1. **Connect via RDP:**
   ```bash
   xfreerdp /v:<target_ip> /u:rdpuser /p:password
   ```

2. **Navigate to flag location:**
   - Open File Explorer
   - Navigate to: `C:\Users\rdpuser\flag.txt` or `/home/rdpuser/flag.txt`

3. **View flag:**
   - Open flag.txt in Notepad
   - Copy the flag content

### Step 7: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mult1pl3_p0rts}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Performed full port scan (all ports or 1-1000)
- ✅ Identified all three services: HTTP (80), SMB (445), RDP (3389)
- ✅ Successfully accessed flag via at least one service
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Only scanning default ports
- Not recognizing all three services
- Missing one of the open ports

## Hints for Struggling Students

1. Use `nmap -p-` for all ports or `nmap -p 1-1000` for common ports
2. Look for ports 80, 445, and 3389
3. The flag is accessible via any of the three services
4. Try HTTP first as it's the simplest

